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

from fastapi import File, UploadFile, Form
from fastapi.responses import StreamingResponse
from typing import List, Optional
from telegram import InputFile
import asyncio, time, io

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
    filename = f"DASTYOR_OCR_{ts}.docx"
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



@app.post("/api/upload_pdf")
async def api_upload_pdf(telegram_id: str = Form(...), files: List[UploadFile] = File(...)):
    try:
        chat_id = int(telegram_id)
        import time, asyncio
        os.makedirs("temp", exist_ok=True)
        
        # Save uploaded files with unique names
        img_paths = []
        ts = int(time.time())
        for i, file in enumerate(files):
            ext = os.path.splitext(file.filename)[1] or ".jpg"
            path = f"temp/pdf_{chat_id}_{ts}_{i}{ext}"
            content = await file.read()
            with open(path, "wb") as f:
                f.write(content)
            img_paths.append(path)
        
        if not img_paths:
            return {"error": "Fayl yuklanmadi"}
        
        logger.info(f"PDF task: {len(img_paths)} images for user {chat_id}")
        msg = await application.bot.send_message(
            chat_id=chat_id,
            text=f"⏳ {len(img_paths)} ta rasm qabul qilindi. PDF tayyorlanmoqda..."
        )
        
        async def run_pdf_task():
            pdf_path = f"temp/merged_{chat_id}_{ts}.pdf"
            try:
                from bot.services.pdf_service import images_to_pdf
                # Run CPU-bound PDF creation in executor thread
                await asyncio.get_event_loop().run_in_executor(
                    None, images_to_pdf, img_paths, pdf_path
                )
                
                if not os.path.exists(pdf_path):
                    raise FileNotFoundError("PDF fayl yaratilmadi")
                
                with open(pdf_path, 'rb') as f:
                    await application.bot.send_document(
                        chat_id=chat_id,
                        document=InputFile(f, filename=f"DastyorAI_{ts}.pdf"),
                        caption=f"✅ **PDF tayyor!**\n📄 {len(img_paths)} ta rasm birlashtirildi.",
                        parse_mode="Markdown"
                    )
                await application.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
                logger.info(f"PDF sent to {chat_id} successfully")
                
            except Exception as ex:
                logger.error(f"PDF task error: {ex}", exc_info=True)
                try:
                    await application.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=msg.message_id,
                        text=f"❌ PDF yaratishda xatolik: {str(ex)[:200]}"
                    )
                except Exception:
                    pass
            finally:
                # Cleanup
                for p in img_paths:
                    try:
                        if os.path.exists(p): os.remove(p)
                    except: pass
                try:
                    if os.path.exists(pdf_path): os.remove(pdf_path)
                except: pass
        
        asyncio.create_task(run_pdf_task())
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Upload PDF API error: {e}", exc_info=True)
        return {"error": str(e)}


@app.get("/health")
async def health():
    return {"status": "healthy"}

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
