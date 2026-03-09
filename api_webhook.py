import os
import logging
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from telegram import Update
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from main import setup_application

# Setup Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Application
application = setup_application()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize application
    await application.initialize()
    await application.start()
    
    # Set Webhook automatically on startup
    webhook_url = "https://dastyor-ai.onrender.com/webhook"
    logger.info(f"Setting webhook to: {webhook_url}")
    await application.bot.set_webhook(url=webhook_url, drop_pending_updates=True)
    
    logger.info("🚀 Webhook Application Started")
    yield
    # Shutdown
    await application.stop()
    await application.shutdown()
    logger.info("🛑 Webhook Application Stopped")

from fastapi.responses import RedirectResponse

app = FastAPI(lifespan=lifespan)

# ── CORS: allow webapp pages to call /api/* from any origin ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve Web App Files
app.mount("/webapp", StaticFiles(directory="webapp"), name="webapp")

@app.get("/")
async def root():
    return RedirectResponse(url="/webapp/index.html")

from pydantic import BaseModel
from fastapi import File, UploadFile, Form, Header, Query
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Optional, Literal
from telegram import InputFile
import asyncio, time, io

from bot.services.render_service import (
    generate_cv_pdf, generate_cv_word, build_cv_context, safe_filename,
    generate_obyektivka_pdf, generate_obyektivka_word, build_obyektivka_context,
)

SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://dastyor-ai.onrender.com")


# ═══════════════════════════════════════════════════════════════════════════
# HELPER: Resolve telegram_id from ANY source (token > URL param > form)
# ═══════════════════════════════════════════════════════════════════════════
def _resolve_uid(
    telegram_id_param: Optional[str] = None,
    session_token: Optional[str] = None,
) -> Optional[str]:
    """
    Priority order:
      1. Session token (most secure — validated against our DB)
      2. Raw telegram_id param (from URL / form, legacy / WebApp fallback)
    Returns the telegram_id string or None.
    """
    if session_token:
        from bot.services.session_service import resolve_telegram_id
        uid = resolve_telegram_id(session_token)
        if uid:
            return uid
    if telegram_id_param and telegram_id_param.strip().isdigit():
        return telegram_id_param.strip()
    return None


# ═══════════════════════════════════════════════════════════════════════════
# /api/auth — Create session from Telegram identity
# Called by index.html after Telegram WebApp is ready.
# ═══════════════════════════════════════════════════════════════════════════
class AuthRequest(BaseModel):
    telegram_id: int
    first_name:  str = ""
    username:    str = ""
    photo_url:   str = ""

@app.post("/api/auth")
async def api_auth(req: AuthRequest):
    """
    Exchange Telegram identity → server session token.
    The token is stored in sessionStorage and sent back
    with every subsequent API request.
    """
    try:
        from bot.services.session_service import create_session
        token = create_session(
            telegram_id = req.telegram_id,
            first_name  = req.first_name,
            username    = req.username,
            photo_url   = req.photo_url,
        )
        # Also upsert the user profile in the CRM
        from bot.services.user_service import track_user_activity, save_chat_id
        class _FakeUser:
            id = req.telegram_id
            first_name = req.first_name
            username   = req.username
        track_user_activity(_FakeUser(), command="web_auth")
        # Persist chat_id so file-delivery endpoints can find the correct chat
        save_chat_id(req.telegram_id, req.telegram_id)  # For private chats uid == chat_id

        return {"ok": True, "token": token, "telegram_id": req.telegram_id}
    except Exception as e:
        logger.error(f"/api/auth error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)[:200])


# ═══════════════════════════════════════════════════════════════════════════
# /api/me — Return user profile for given token or telegram_id
# ═══════════════════════════════════════════════════════════════════════════
@app.get("/api/me")
async def api_me(
    token:       Optional[str] = Query(None),
    telegram_id: Optional[str] = Query(None),
):
    uid = _resolve_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")

    from bot.services.user_service       import get_user_profile
    from bot.services.settings_service   import is_premium
    from bot.services.session_service    import get_session_by_telegram_id

    profile = get_user_profile(uid) or {}
    session = get_session_by_telegram_id(uid) or {}

    return {
        "ok"          : True,
        "telegram_id" : uid,
        "first_name"  : session.get("first_name", profile.get("first_name", "")),
        "username"    : session.get("username",   profile.get("username", "")),
        "photo_url"   : session.get("photo_url",  ""),
        "is_premium"  : is_premium(int(uid)),
        "files_processed": profile.get("files_processed", 0),
        "joined_at"   : profile.get("joined_at", ""),
        "last_active" : profile.get("last_active", ""),
    }


# ═══════════════════════════════════════════════════════════════════════════
# /api/translit — Server-side Cyrillic ↔ Latin (consistent with bot)
# ═══════════════════════════════════════════════════════════════════════════
class TranslitRequest(BaseModel):
    text:      str
    direction: str   # "krill_to_lotin" | "lotin_to_krill"

@app.post("/api/translit")
async def api_translit(req: TranslitRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Matn bo'sh bo'lishi mumkin emas")
    if len(req.text) > 50_000:
        raise HTTPException(status_code=400, detail="Matn 50 000 belgidan oshmasligi kerak")

    valid = {"krill_to_lotin", "lotin_to_krill"}
    if req.direction not in valid:
        raise HTTPException(status_code=400, detail=f"Noto'g'ri yo'nalish: {req.direction}")

    try:
        from bot.services.transliterate_service import transliterate
        result = transliterate(req.text, req.direction)  # type: ignore[arg-type]
        return {"ok": True, "result": result, "direction": req.direction}
    except Exception as e:
        logger.error(f"/api/translit error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)[:200])


# ═══════════════════════════════════════════════════════════════════════════
# /api/bot-link — Generate deep-link for a bot command
# Lets the website open the bot at exactly the right state.
# ═══════════════════════════════════════════════════════════════════════════
BOT_USERNAME = os.getenv("BOT_USERNAME", "DastyorAiBot")
WEBAPP_BASE  = os.getenv("WEBAPP_BASE",  "https://dastyor-ai.onrender.com/webapp")

@app.get("/api/bot-link")
async def api_bot_link(
    action:      str = Query(..., description="cv | obyektivka | ocr | pdf | translit | translate"),
    telegram_id: Optional[str] = Query(None),
):
    """
    Returns a t.me deep-link that opens the bot AND, for web-first
    actions, also returns the direct webapp URL so the website can
    redirect without going through Telegram.
    """
    page_map = {
        "cv"         : "cv.html",
        "obyektivka" : "obyektivka.html",
        "ocr"        : "ocr.html",
        "pdf"        : "img2pdf.html",
        "translit"   : "translit.html",
        "translate"  : "translate.html",
        "premium"    : "premium.html",
    }
    page = page_map.get(action)
    if not page:
        raise HTTPException(status_code=400, detail=f"Noma'lum action: {action}")

    # Deep-link: t.me/BotUsername?start=action
    bot_link  = f"https://t.me/{BOT_USERNAME}?start={action}"
    # Direct webapp URL (already has telegram_id → user stays logged in)
    tid_param = f"?telegram_id={telegram_id}" if telegram_id else ""
    webapp_url = f"{WEBAPP_BASE}/{page}{tid_param}"

    return {"ok": True, "bot_link": bot_link, "webapp_url": webapp_url, "action": action}


# ═══════════════════════════════════════════════════════════════════════════
# /api/stats — Per-user usage statistics (for the website dashboard)
# ═══════════════════════════════════════════════════════════════════════════
@app.get("/api/stats")
async def api_stats(
    token:       Optional[str] = Query(None),
    telegram_id: Optional[str] = Query(None),
):
    uid = _resolve_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")

    from bot.services.user_service     import get_user_profile
    from bot.services.settings_service import is_premium
    from bot.services.usage_tracker    import can_use

    profile = get_user_profile(uid) or {}
    premium = is_premium(int(uid))

    return {
        "ok"              : True,
        "telegram_id"     : uid,
        "is_premium"      : premium,
        "files_processed" : profile.get("files_processed", 0),
        "sessions"        : profile.get("sessions", 1),
        "last_service"    : profile.get("last_service", ""),
        "last_active"     : profile.get("last_active", ""),
        "joined_at"       : profile.get("joined_at", ""),
    }


# ═══════════════════════════════════════════════════════════════════════════
# /api/notify — Push a text notification to user's Telegram chat
# Lets any website action trigger a Telegram message.
# ═══════════════════════════════════════════════════════════════════════════
class NotifyRequest(BaseModel):
    telegram_id : int
    message     : str
    token       : Optional[str] = None

@app.post("/api/notify")
async def api_notify(req: NotifyRequest):
    """Send a plain-text notification to the user's Telegram chat."""
    # Validate token OR just trust telegram_id (within same server — no public exposure risk)
    uid = _resolve_uid(str(req.telegram_id), req.token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")

    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Xabar bo'sh")
    if len(req.message) > 4000:
        raise HTTPException(status_code=400, detail="Xabar 4000 belgi oshmasligi kerak")

    try:
        await application.bot.send_message(
            chat_id    = int(uid),
            text       = req.message,
            parse_mode = "HTML",
        )
        return {"ok": True}
    except Exception as e:
        logger.warning(f"/api/notify failed for {uid}: {e}")
        raise HTTPException(status_code=502, detail=f"Telegram xatosi: {str(e)[:200]}")


# ═══════════════════════════════════════════════════════════════════════════
# /api/translate (existing, kept in place)
# ═══════════════════════════════════════════════════════════════════════════
class TranslateRequest(BaseModel):
    text: str
    direction: str

@app.post("/api/translate")
async def api_translate(req: TranslateRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Matn bo'sh bo'lishi mumkin emas")
    if len(req.text) > 5000:
        raise HTTPException(status_code=400, detail="Matn 5000 belgidan oshmasligi kerak")

    valid_dirs = {"uz_en", "en_uz", "ru_uz", "uz_ru", "ru_en"}
    if req.direction not in valid_dirs:
        raise HTTPException(status_code=400, detail=f"Noto'g'ri yo'nalish: {req.direction}")

    try:
        from bot.services.ai_service import translate_text
        result = await translate_text(req.text, req.direction)
        if not result or result.startswith("Tarjimada xato") or result.startswith("AI model"):
            raise HTTPException(status_code=502, detail=result or "Tarjima bo'sh qaytdi")
        return {"ok": True, "translated_text": result, "direction": req.direction}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Translate API error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Tarjima serveri xatosi: {str(e)[:200]}")


# ─────────────────────────────────────────────────────────────────────
# /api/ocr_direct — Website-first OCR endpoint
#
# Architecture:
#   1. Image uploaded from browser (no telegram_id required)
#   2. Gemini OCR extracts text as HTML
#   3. DOCX created in-memory via python-docx
#   4. DOCX bytes streamed back to browser → auto-download
#   5. If telegram_id provided → background task sends copy to Telegram
#
# Why old /api/upload_ocr was broken:
#   - Required telegram_id (Form required field) → error without Telegram
#   - Imported non-existent process_ocr_logic from smart_logic → ImportError
#   - int('') raises ValueError at line 1
#   - DOCX was deleted after bot send — never returned to browser
# ─────────────────────────────────────────────────────────────────────
@app.post("/api/ocr_direct")
async def api_ocr_direct(
    file: UploadFile = File(...),
    telegram_id: Optional[str] = Form(None),   # optional — works without Telegram
):
    ts = int(time.time())
    img_path  = f"temp/ocr_{ts}_{file.filename or 'img.jpg'}"
    docx_path = f"temp/ocr_{ts}_result.docx"
    os.makedirs("temp", exist_ok=True)

    # ── 1. Save uploaded image to disk ──────────────────────────────
    try:
        raw = await file.read()
        if len(raw) == 0:
            raise HTTPException(status_code=400, detail="Fayl bo'sh")
        if len(raw) > 15 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Fayl 15 MB dan oshmasligi kerak")
        with open(img_path, "wb") as f:
            f.write(raw)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fayl saqlashda xato: {e}")

    # ── 2. OCR: extract text from image using Gemini ─────────────────
    try:
        from bot.services.ocr_service import extract_text_from_image
        html_text = await extract_text_from_image(img_path)
    except Exception as e:
        logger.error(f"OCR extract error: {e}", exc_info=True)
        _cleanup(img_path)
        raise HTTPException(status_code=502, detail=f"OCR xatosi: {str(e)[:200]}")

    if not html_text or not html_text.strip():
        _cleanup(img_path)
        raise HTTPException(status_code=422, detail="Rasmdan matn ajratib bo'lmadi. Aniqroq rasm yuboring.")

    # ── 3. Build DOCX in a thread (CPU-bound) ────────────────────────
    try:
        from docx import Document
        from bot.handlers.ocr_to_word import add_html_to_docx

        def build_docx() -> bytes:
            doc = Document()
            doc.add_heading("OCR Natijasi", 0)
            try:
                add_html_to_docx(doc, html_text)
            except Exception as parse_err:
                logger.warning(f"HTML parse fallback: {parse_err}")
                doc.add_paragraph(html_text)  # raw text fallback
            # Save to bytes buffer (no disk needed)
            buf = io.BytesIO()
            doc.save(buf)
            buf.seek(0)
            return buf.read()

        docx_bytes = await asyncio.get_event_loop().run_in_executor(None, build_docx)
    except Exception as e:
        logger.error(f"DOCX build error: {e}", exc_info=True)
        _cleanup(img_path)
        raise HTTPException(status_code=500, detail=f"Word hujjat yaratishda xato: {str(e)[:200]}")

    # ── 4. Optional Telegram send (background, non-blocking) ─────────
    if telegram_id and telegram_id.strip().isdigit():
        chat_id = int(telegram_id)

        async def send_to_telegram():
            try:
                buf = io.BytesIO(docx_bytes)
                buf.name = f"OCR_Natija_{ts}.docx"
                await application.bot.send_document(
                    chat_id=chat_id,
                    document=InputFile(buf, filename=buf.name),
                    caption="✅ Rasm Word ga aylantirildi!\n📎 Fayl tayyor.",
                )
                logger.info(f"OCR DOCX sent to Telegram chat {chat_id}")
            except Exception as tg_err:
                logger.warning(f"Telegram send failed (non-fatal): {tg_err}")

        asyncio.create_task(send_to_telegram())

    # ── 5. Cleanup temp image ─────────────────────────────────────────
    _cleanup(img_path)

    # ── 6. Stream DOCX bytes to browser → triggers auto-download ─────
    filename = f"DASTYOR_OCR_{ts}_@DastyorAiBot.docx"
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _cleanup(*paths):
    """Safely remove temp files."""
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except Exception:
            pass


# ── Legacy endpoint kept for backward compatibility ───────────────────
@app.post("/api/upload_ocr")
async def api_upload_ocr(telegram_id: str = Form(...), files: List[UploadFile] = File(...)):
    """
    Legacy endpoint — kept for backward compat.
    New website code should use /api/ocr_direct instead.
    """
    try:
        chat_id = int(telegram_id)
        legacy_ts = int(time.time())
        os.makedirs("temp", exist_ok=True)
        img_paths = []
        for f in files:
            path = f"temp/legacy_ocr_{legacy_ts}_{f.filename}"
            content = await f.read()
            with open(path, "wb") as fh:
                fh.write(content)
            img_paths.append(path)

        async def run_legacy_ocr():
            from bot.services.ocr_service import extract_text_from_image
            from bot.handlers.ocr_to_word import add_html_to_docx
            from docx import Document
            try:
                msg = await application.bot.send_message(
                    chat_id=chat_id,
                    text="⏳ Rasm qabul qilindi. OCR qilinmoqda..."
                )
                for img_path in img_paths:
                    html_text = await extract_text_from_image(img_path)
                    if not html_text:
                        continue
                    ts2 = int(time.time())
                    docx_path = f"temp/legacy_{chat_id}_{ts2}.docx"
                    doc = Document()
                    doc.add_heading("OCR Natijasi", 0)
                    add_html_to_docx(doc, html_text)
                    doc.save(docx_path)
                    with open(docx_path, "rb") as df:
                        await application.bot.send_document(
                            chat_id=chat_id,
                            document=InputFile(df, filename=f"OCR_{ts2}.docx"),
                            caption="✅ Word fayl tayyor!"
                        )
                    _cleanup(docx_path)
                await application.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
            except Exception as ex:
                logger.error(f"Legacy OCR error: {ex}", exc_info=True)
            finally:
                for p in img_paths:
                    _cleanup(p)

        asyncio.create_task(run_legacy_ocr())
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Upload OCR API error: {e}", exc_info=True)
        return {"error": str(e)}



@app.post("/api/pdf_direct")
async def api_pdf_direct(
    files: List[UploadFile] = File(...),
    telegram_id: Optional[str] = Form(None)
):
    try:
        import time, asyncio
        os.makedirs("temp", exist_ok=True)
        
        # Save uploaded files with unique names
        img_paths = []
        ts = int(time.time())
        for i, file in enumerate(files):
            ext = os.path.splitext(file.filename)[1] or ".jpg"
            path = f"temp/pdf_req_{ts}_{i}{ext}"
            content = await file.read()
            with open(path, "wb") as f:
                f.write(content)
            img_paths.append(path)
        
        if not img_paths:
            raise HTTPException(status_code=400, detail="Fayl yuklanmadi")
        
        pdf_path = f"temp/merged_{ts}.pdf"
        
        # CPU-bound PDF creation
        try:
            from bot.services.pdf_service import images_to_pdf
            await asyncio.get_event_loop().run_in_executor(
                None, images_to_pdf, img_paths, pdf_path
            )
        except Exception as build_err:
            logger.error(f"PDF creation error: {build_err}", exc_info=True)
            _cleanup(*img_paths)
            raise HTTPException(status_code=500, detail=f"PDF yaratishda xato: {build_err}")
            
        if not os.path.exists(pdf_path):
            _cleanup(*img_paths)
            raise HTTPException(status_code=500, detail="PDF fayl yaratilmadi")
            
        # Read the generated PDF into memory so we can safely delete the file
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
            
        # Cleanup ALL temp files now that we have bytes
        _cleanup(pdf_path, *img_paths)
        
        # Optional: Send to Telegram in background
        if telegram_id and telegram_id.strip().isdigit():
            chat_id = int(telegram_id)
            async def send_pdf_to_telegram():
                try:
                    buf = io.BytesIO(pdf_bytes)
                    buf.name = f"DASTYOR_AI_Rasmlar_{ts}_@DastyorAiBot.pdf"
                    await application.bot.send_document(
                        chat_id=chat_id,
                        document=InputFile(buf, filename=buf.name),
                        caption=f"✅ **PDF tayyor!**\n📄 {len(img_paths)} ta rasm birlashtirildi.",
                        parse_mode="Markdown"
                    )
                    logger.info(f"PDF sent to {chat_id} successfully")
                except Exception as tg_err:
                    logger.warning(f"Telegram send failed (non-fatal): {tg_err}")
                    
            asyncio.create_task(send_pdf_to_telegram())
            
        # Stream back to browser
        filename = f"DASTYOR_AI_Rasmlar_{ts}_@DastyorAiBot.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload PDF API error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "healthy"}


# ═══════════════════════════════════════════════════════════════════════════
# /api/upload_to_telegram — Direct file sender to Telegram from Frontend JS
# ═══════════════════════════════════════════════════════════════════════════
@app.post("/api/upload_to_telegram")
async def api_upload_to_telegram(
    file: UploadFile = File(...),
    telegram_id: str = Form(None),
    token: str = Form(None),
    caption: str = Form("")
):
    uid = _resolve_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    try:
        content = await file.read()
        logger.info(f"Sending frontend-generated file {file.filename} to UID {uid}")
        await application.bot.send_document(
            chat_id=uid,
            document=content,
            filename=file.filename,
            caption=caption or "✅ Faylingiz tayyorlandi!"
        )
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error sending file via /api/upload_to_telegram: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}

# ═══════════════════════════════════════════════════════════════════════════
# /api/generate_cv — CV DOCX generator (Website → Server → Browser + Telegram)
# ─────────────────────────────────────────────────────────────────────────────
# Architecture:
#   1. Website POSTs JSON payload (form fields + template choice)
#   2. Server calls bot.services.doc_generator.generate_cv_docx()
#   3. DOCX bytes streamed to browser → auto-download
#   4. If telegram_id provided → background sends same file to Telegram chat
# ═══════════════════════════════════════════════════════════════════════════
class CVRequest(BaseModel):
    telegram_id : Optional[int] = None
    token       : Optional[str] = None
    # CV form fields
    name        : str = ""
    spec        : str = ""
    phone       : str = ""
    email       : str = ""
    loc         : str = ""
    addr        : str = ""
    birth       : str = ""
    place       : str = ""
    nation      : str = ""
    langs       : str = ""
    about       : str = ""
    template    : str = "minimal"
    works       : list = []
    education_list: list = []
    skills      : str = ""

@app.post("/api/generate_cv")
async def api_generate_cv(req: CVRequest):
    """
    Generate a CV DOCX on the server from website form data.
    • Returns the file as a streaming download for the browser.
    • Simultaneously sends the file to the user’s Telegram chat (background).
    """
    ts = int(time.time())
    os.makedirs("temp", exist_ok=True)

    # Resolve Telegram identity
    uid_str = _resolve_uid(
        str(req.telegram_id) if req.telegram_id else None,
        req.token
    )

    # Build payload for doc_generator (mirrors webapp_data.py schema)
    payload = req.dict(exclude={"telegram_id", "token"})

    # CPU-bound generation in thread
    try:
        from bot.services.doc_generator import generate_cv_docx
        docx_path = await asyncio.get_event_loop().run_in_executor(
            None, generate_cv_docx, payload
        )
    except Exception as e:
        logger.error(f"/api/generate_cv build error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"CV yaratishda xato: {str(e)[:200]}")

    if not docx_path or not os.path.exists(docx_path):
        raise HTTPException(status_code=500, detail="CV fayl yaratilmadi")

    with open(docx_path, "rb") as fh:
        docx_bytes = fh.read()
    _cleanup(docx_path)

    # ── Background Telegram delivery ────────────────────────────────────
    if uid_str:
        from bot.services.user_service import get_chat_id, increment_file_count
        chat_id = get_chat_id(int(uid_str)) or int(uid_str)
        increment_file_count(int(uid_str), "CV Generator")

        async def _send_cv():
            try:
                buf = io.BytesIO(docx_bytes)
                safe = (req.name or "CV").replace(" ", "_")[:30]
                buf.name = f"DASTYOR_CV_{safe}_{ts}_@DastyorAiBot.docx"
                await application.bot.send_document(
                    chat_id=chat_id,
                    document=InputFile(buf, filename=buf.name),
                    caption=(
                        f"✅ <b>CV tayyor!</b>\n"
                        f"📄 <b>{req.name or 'CV'}</b>\n"
                        f"🆆 Shablon: <i>{req.template}</i>\n"
                        f"📎 Veb-saytdan ham yuklab olishingiz mumkin."
                    ),
                    parse_mode="HTML",
                )
                logger.info(f"CV DOCX sent to Telegram chat {chat_id}")
            except Exception as tg_err:
                logger.warning(f"CV Telegram send failed (non-fatal): {tg_err}")

        asyncio.create_task(_send_cv())

    # ── Stream to browser ───────────────────────────────────────────────
    safe_name = (req.name or "CV").replace(" ", "_")[:30]
    filename = f"DASTYOR_CV_{safe_name}_{ts}_@DastyorAiBot.docx"
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ═══════════════════════════════════════════════════════════════════════════
# /api/get_oby_data — Fetch temporary parsed data for Obyektivka
# ═══════════════════════════════════════════════════════════════════════════
@app.get("/api/get_oby_data")
async def api_get_oby_data(
    token: str = Query(None),
    telegram_id: str = Query(None),
):
    uid = _resolve_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    
    path = f"temp/oby_data_{uid}.json"
    if os.path.exists(path):
        import json
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {"ok": True, "data": data}
        except Exception as e:
            logger.error(f"Error reading oby_data: {e}")
    return {"ok": False}

# ═══════════════════════════════════════════════════════════════════════════
# /api/generate_obyektivka— Obyektivka DOCX generator
# ═══════════════════════════════════════════════════════════════════════════
class ObyektivkaRequest(BaseModel):
    telegram_id : Optional[int] = None
    token       : Optional[str] = None
    format      : str = "word"      # "word" | "pdf"
    lang        : str = "uz_lat"    # uz_lat | uz_cyr | en | ru
    # personal info
    fullname    : str = ""
    birthdate   : str = ""
    birthplace  : str = ""
    nation      : str = ""
    party       : str = ""
    education   : str = ""
    graduated   : str = ""
    specialty   : str = ""
    degree      : str = ""
    scientific_title: str = ""
    languages   : str = ""
    military_rank: str = ""
    awards      : str = ""
    deputy      : str = ""
    work_experience: list = []
    relatives   : list = []

@app.post("/api/generate_obyektivka")
async def api_generate_obyektivka(req: ObyektivkaRequest):
    """
    Generate an Obyektivka (Ma’lumotnoma) DOCX/PDF from website form data.
    • Returns the file as a streaming download for the browser.
    • Sends the same file to the user’s Telegram chat in the background.
    """
    ts = int(time.time())
    os.makedirs("temp", exist_ok=True)

    uid_str = _resolve_uid(
        str(req.telegram_id) if req.telegram_id else None,
        req.token
    )

    doc_data = {
        "lang"            : req.lang,
        "fullname"        : req.fullname,
        "birthdate"       : req.birthdate,
        "birthplace"      : req.birthplace,
        "nation"          : req.nation,
        "party"           : req.party,
        "education"       : req.education,
        "graduated"       : req.graduated,
        "specialty"       : req.specialty,
        "degree"          : req.degree,
        "scientific_title": req.scientific_title,
        "languages"       : req.languages,
        "military_rank"   : req.military_rank,
        "awards"          : req.awards,
        "deputy"          : req.deputy,
        "work_experience" : req.work_experience,
        "relatives"       : req.relatives,
    }

    try:
        from bot.services.doc_generator import generate_obyektivka_docx, convert_to_pdf_safe
        docx_path = await asyncio.get_event_loop().run_in_executor(
            None, generate_obyektivka_docx, doc_data
        )
    except Exception as e:
        logger.error(f"/api/generate_obyektivka build error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Obyektivka yaratishda xato: {str(e)[:200]}")

    if not docx_path or not os.path.exists(docx_path):
        raise HTTPException(status_code=500, detail="Obyektivka fayl yaratilmadi")

    final_path = docx_path
    is_pdf = req.format.lower() == "pdf"

    if is_pdf:
        pdf_path = await asyncio.get_event_loop().run_in_executor(
            None, convert_to_pdf_safe, docx_path
        )
        if pdf_path and os.path.exists(pdf_path):
            final_path = pdf_path
        else:
            is_pdf = False  # fallback to DOCX

    with open(final_path, "rb") as fh:
        file_bytes = fh.read()
    _cleanup(docx_path)
    if final_path != docx_path:
        _cleanup(final_path)

    ext = "pdf" if is_pdf else "docx"
    mime = "application/pdf" if is_pdf else \
           "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    # ── Background Telegram delivery ────────────────────────────────────
    if uid_str:
        from bot.services.user_service import get_chat_id, increment_file_count
        chat_id = get_chat_id(int(uid_str)) or int(uid_str)
        increment_file_count(int(uid_str), "Obyektivka Generator")

        async def _send_oby():
            try:
                buf = io.BytesIO(file_bytes)
                safe = (req.fullname or "Obyektivka").replace(" ", "_")[:30]
                buf.name = f"DASTYOR_Obyektivka_{safe}_{ts}_@DastyorAiBot.{ext}"
                await application.bot.send_document(
                    chat_id=chat_id,
                    document=InputFile(buf, filename=buf.name),
                    caption=(
                        f"✅ <b>Obyektivka tayyor!</b>\n"
                        f"👤 <b>{req.fullname or 'Ma’lumotnoma'}</b>\n"
                        f"📎 Format: <i>{ext.upper()}</i>\n"
                        f"📥 Veb-saytdan ham yuklab olishingiz mumkin."
                    ),
                    parse_mode="HTML",
                )
                logger.info(f"Obyektivka sent to Telegram chat {chat_id}")
            except Exception as tg_err:
                logger.warning(f"Obyektivka Telegram send failed (non-fatal): {tg_err}")

        asyncio.create_task(_send_oby())

    # ── Stream to browser ───────────────────────────────────────────────
    safe_name = (req.fullname or "Obyektivka").replace(" ", "_")[:30]
    filename = f"DASTYOR_Obyektivka_{safe_name}_{ts}_@DastyorAiBot.{ext}"
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )




# ═══════════════════════════════════════════════════════════════════════════
# /api/export_cv  — Server-side CV export (PDF or Word)
# ═══════════════════════════════════════════════════════════════════════════
class ExportCVRequest(BaseModel):
    telegram_id : Optional[int]  = None
    token       : Optional[str]  = None
    format      : str            = "pdf"   # "pdf" | "word"
    lang        : str            = "uz_lat"
    # CV fields (mirrors CVRequest above)
    name        : str  = ""
    spec        : str  = ""
    phone       : str  = ""
    email       : str  = ""
    loc         : str  = ""
    addr        : str  = ""
    birth       : str  = ""
    place       : str  = ""
    nation      : str  = ""
    langs       : str  = ""
    about       : str  = ""
    template    : str  = "minimal"
    works       : list = []
    education_list: list = []
    skills      : str  = ""
    img         : str  = ""   # absolute URL of profile photo (optional)

@app.post("/api/export_cv")
async def api_export_cv(req: ExportCVRequest):
    """
    Server-side CV export.
    Renders the SAME Jinja2 template used for the browser preview, so
    the exported file is pixel-perfect regardless of client environment.
    """
    ts = int(time.time())
    uid_str = _resolve_uid(str(req.telegram_id) if req.telegram_id else None, req.token)
    fmt = req.format.lower()
    data = req.dict(exclude={"telegram_id", "token", "format"})
    safe = safe_filename(req.name or "CV")
    bot_suffix = "_@DastyorAiBot"

    if fmt == "word":
        # ── Word export — real .docx (python-docx, mobile-compatible) ──
        filename = f"DASTYOR_CV_{safe}_{ts}{bot_suffix}.docx"
        from bot.services.doc_generator import generate_cv_docx
        docx_path = await asyncio.get_event_loop().run_in_executor(None, generate_cv_docx, data)
        if not docx_path or not os.path.exists(docx_path):
            raise HTTPException(status_code=500, detail="Word fayl yaratishda xato")
        with open(docx_path, "rb") as fh:
            file_bytes = fh.read()
        try:
            os.remove(docx_path)
        except Exception:
            pass
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        # ── PDF export (Playwright → exact browser render) ─────────────
        filename = f"DASTYOR_CV_{safe}_{ts}{bot_suffix}.pdf"
        pdf_bytes = await generate_cv_pdf(data, base_url=SITE_BASE_URL)
        if not pdf_bytes:
            # Playwright unavailable → fall back to python-docx PDF
            from bot.services.doc_generator import generate_cv_docx, convert_to_pdf_safe
            docx_path = await asyncio.get_event_loop().run_in_executor(None, generate_cv_docx, data)
            pdf_path = convert_to_pdf_safe(docx_path) if docx_path else None
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as fh:
                    pdf_bytes = fh.read()
                for p in [pdf_path, docx_path]:
                    try: os.remove(p)
                    except: pass
            else:
                logger.error("All PDF generation methods failed inside api_webhook.py")
                raise HTTPException(status_code=500, detail="PDF yaratishda xato")
        file_bytes = pdf_bytes
        media_type = "application/pdf"

    # ── Background Telegram delivery ────────────────────────────────────
    if uid_str:
        from bot.services.user_service import increment_file_count
        increment_file_count(int(uid_str), f"CV Export {fmt.upper()}")

        async def _send():
            try:
                buf = io.BytesIO(file_bytes)
                buf.name = filename
                chat_id = int(uid_str)
                await application.bot.send_document(
                    chat_id=chat_id,
                    document=InputFile(buf, filename=filename),
                    caption=(
                        f"✅ <b>CV tayyor!</b>\n"
                        f"👤 <b>{req.name}</b>  · 🎨 {req.template}\n"
                        f"📎 <code>{filename}</code>"
                    ),
                    parse_mode="HTML",
                )
            except Exception as tg_err:
                logger.warning(f"CV export Telegram send failed: {tg_err}")

        asyncio.create_task(_send())

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ═══════════════════════════════════════════════════════════════════════════
# /api/export_obyektivka  — Server-side Obyektivka export
# ═══════════════════════════════════════════════════════════════════════════
class ExportObyektivkaRequest(BaseModel):
    telegram_id    : Optional[int] = None
    token          : Optional[str] = None
    format         : str           = "pdf"  # "pdf" | "word"
    lang           : str           = "uz_lat"
    fullname       : str = ""
    birthdate      : str = ""
    birthplace     : str = ""
    nation         : str = ""
    party          : str = ""
    education      : str = ""
    graduated      : str = ""
    specialty      : str = ""
    degree         : str = ""
    scientific_title: str = ""
    languages      : str = ""
    military_rank  : str = ""
    awards         : str = ""
    deputy         : str = ""
    address        : str = ""
    phone          : str = ""
    work_experience: list = []
    relatives      : list = []

@app.post("/api/export_obyektivka")
async def api_export_obyektivka(req: ExportObyektivkaRequest):
    """
    Server-side Obyektivka export — same template as browser preview.
    """
    ts  = int(time.time())
    uid_str = _resolve_uid(str(req.telegram_id) if req.telegram_id else None, req.token)
    fmt  = req.format.lower()
    data = req.dict(exclude={"telegram_id", "token", "format"})
    safe = safe_filename(req.fullname or "Obyektivka")
    bot_suffix = "_@DastyorAiBot"

    if fmt == "word":
        # ── Word export — real .docx (python-docx, mobile-compatible) ──
        filename = f"DASTYOR_Obyektivka_{safe}_{ts}{bot_suffix}.docx"
        from bot.services.doc_generator import generate_obyektivka_docx
        docx_path = await asyncio.get_event_loop().run_in_executor(None, generate_obyektivka_docx, data)
        if not docx_path or not os.path.exists(docx_path):
            raise HTTPException(status_code=500, detail="Word fayl yaratishda xato")
        with open(docx_path, "rb") as fh:
            file_bytes = fh.read()
        try:
            os.remove(docx_path)
        except Exception:
            pass
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        filename  = f"DASTYOR_Obyektivka_{safe}_{ts}{bot_suffix}.pdf"
        pdf_bytes = await generate_obyektivka_pdf(data, base_url=SITE_BASE_URL)
        if not pdf_bytes:
            from bot.services.doc_generator import generate_obyektivka_docx, convert_to_pdf_safe
            docx_path = await asyncio.get_event_loop().run_in_executor(None, generate_obyektivka_docx, data)
            pdf_path  = convert_to_pdf_safe(docx_path) if docx_path else None
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as fh:
                    pdf_bytes = fh.read()
                for p in [pdf_path, docx_path]:
                    try: os.remove(p)
                    except: pass
            else:
                raise HTTPException(status_code=500, detail="PDF yaratishda xato")
        file_bytes = pdf_bytes
        media_type = "application/pdf"

    if uid_str:
        from bot.services.user_service import increment_file_count
        increment_file_count(int(uid_str), f"Obyektivka Export {fmt.upper()}")

        async def _send_oby():
            try:
                buf = io.BytesIO(file_bytes)
                buf.name = filename
                await application.bot.send_document(
                    chat_id=int(uid_str),
                    document=InputFile(buf, filename=filename),
                    caption=(
                        f"✅ <b>Obyektivka tayyor!</b>\n"
                        f"👤 <b>{req.fullname}</b>\n"
                        f"📎 <code>{filename}</code>"
                    ),
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning(f"Obyektivka export Telegram send failed: {e}")

        asyncio.create_task(_send_oby())

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/webhook")

async def webhook(request: Request):
    """
    Handle incoming Telegram updates via POST request.
    """
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return Response(status_code=500)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
