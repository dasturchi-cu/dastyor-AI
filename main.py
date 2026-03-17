"""
Main Bot Entry Point (with Ban Check Middleware)
"""
import os
import io
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    filters, ContextTypes, TypeHandler, CallbackQueryHandler, ChatMemberHandler
)

try:
    load_dotenv()
except: pass

from config import BOT_TOKEN, logger

# ──────────────────────────────────────────────────────────────────────────────
# DASTYOR AI — OCR Backend (FastAPI + PaddleOCR + OpenCV + python-docx)
#
# Endpoints:
#   POST /ocr      → JSON: {"text": "..."}
#   POST /ocr-word → DOCX download with detected text
#
# Note:
# - PaddleOCR is initialized once at server startup.
# - OCR runs in a thread pool (CPU-bound).
#
# Run API mode:
#   RUN_MODE=api uvicorn main:app --host 0.0.0.0 --port 8000
# Run bot mode (default):
#   python main.py
# ──────────────────────────────────────────────────────────────────────────────

try:
    import numpy as np
    import cv2
    from paddleocr import PaddleOCR
    from docx import Document
    from fastapi import FastAPI, UploadFile, File, HTTPException
    from fastapi.responses import StreamingResponse
    from fastapi.middleware.cors import CORSMiddleware
except Exception:
    # Allow bot-only mode even if OCR deps not installed.
    np = None
    cv2 = None
    PaddleOCR = None
    Document = None
    FastAPI = None
    UploadFile = None
    File = None
    HTTPException = Exception
    StreamingResponse = None
    CORSMiddleware = None

_ocr_logger = logging.getLogger("dastyor.ocr")
_OCR_ENGINE = None
_OCR_POOL = ThreadPoolExecutor(max_workers=int(os.getenv("OCR_WORKERS", "2")))

app = FastAPI(title="Dastyor AI OCR API") if FastAPI else None

if app and CORSMiddleware:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _ensure_ocr_deps():
    if any(x is None for x in (np, cv2, PaddleOCR, Document, StreamingResponse)) or app is None:
        raise RuntimeError(
            "OCR dependencies are missing. Install: paddleocr, opencv-python, numpy, python-docx, fastapi, uvicorn"
        )


def preprocess_image_opencv(image_bgr):
    """
    OpenCV preprocessing:
    - grayscale
    - threshold (Otsu)
    Returns a processed image suitable for OCR.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    # Otsu thresholding improves contrast for text
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return th


def extract_text_with_paddle(processed_img) -> str:
    """
    Run PaddleOCR on the processed image and return plain text.
    """
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        raise RuntimeError("OCR engine is not initialized")

    # PaddleOCR works well with 3-channel images; convert if needed.
    if len(processed_img.shape) == 2:
        img_for_ocr = cv2.cvtColor(processed_img, cv2.COLOR_GRAY2BGR)
    else:
        img_for_ocr = processed_img

    # In newer PaddleOCR versions, angle classification is configured at init (use_angle_cls)
    # and .ocr() may not accept cls=...
    result = _OCR_ENGINE.ocr(img_for_ocr) or []
    lines = []
    # result: list[ list[ [box], (text, score) ] ]
    for block in result:
        for item in block or []:
            try:
                text = item[1][0]
            except Exception:
                text = ""
            if text:
                lines.append(text)
    return "\n".join(lines).strip()


def build_docx_bytes(text: str) -> bytes:
    doc = Document()
    for line in (text or "").splitlines():
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


def build_docx_with_image_and_text(image_bytes: bytes, text: str) -> bytes:
    """
    1:1 visual: embed the original image into the DOCX (scaled to page width),
    then put OCR text on the next page (so you still get extracted text).
    """
    from docx.shared import Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()

    # Make margins smaller so image fits better (still printable)
    try:
        section = doc.sections[0]
        section.top_margin = Inches(0.4)
        section.bottom_margin = Inches(0.4)
        section.left_margin = Inches(0.4)
        section.right_margin = Inches(0.4)
    except Exception:
        pass

    # Add image first (visual 1:1). Use file-like object.
    bio = io.BytesIO(image_bytes)
    bio.name = "upload.jpg"
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    # Approx page text width with 0.4" margins on Letter/A4 is ~7.2"
    run.add_picture(bio, width=Inches(7.2))

    # Put OCR text on a new page (optional but keeps requirement "insert detected text")
    doc.add_page_break()
    for line in (text or "").splitlines():
        doc.add_paragraph(line)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


if app:
    @app.on_event("startup")
    async def _startup_init_ocr():
        _ensure_ocr_deps()
        global _OCR_ENGINE
        if _OCR_ENGINE is None:
            lang = os.getenv("PADDLE_OCR_LANG", "en")
            _ocr_logger.info("Initializing PaddleOCR (lang=%s)...", lang)
            # Initialize once
            _OCR_ENGINE = PaddleOCR(lang=lang, use_angle_cls=True)
            _ocr_logger.info("PaddleOCR initialized.")


    async def _read_image_as_bgr(file: UploadFile):
        raw = await file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="Empty file")
        if len(raw) > 15 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 15MB)")
        arr = np.frombuffer(raw, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image")
        return img


    @app.post("/ocr")
    async def ocr_endpoint(file: UploadFile = File(...)):
        """
        Receive image → preprocess (gray + threshold) → PaddleOCR → return JSON text.
        """
        try:
            _ensure_ocr_deps()
            img = await _read_image_as_bgr(file)
            processed = preprocess_image_opencv(img)
            loop = asyncio.get_running_loop()
            text = await loop.run_in_executor(_OCR_POOL, extract_text_with_paddle, processed)
            return {"text": text}
        except HTTPException:
            raise
        except Exception as e:
            _ocr_logger.error("OCR /ocr failed: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail="OCR failed")


    @app.post("/ocr-word")
    async def ocr_word_endpoint(file: UploadFile = File(...)):
        """
        Receive image → OCR → generate DOCX → return as download.
        """
        try:
            _ensure_ocr_deps()
            raw = await file.read()
            if not raw:
                raise HTTPException(status_code=400, detail="Empty file")
            if len(raw) > 15 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="File too large (max 15MB)")
            arr = np.frombuffer(raw, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                raise HTTPException(status_code=400, detail="Invalid image")
            processed = preprocess_image_opencv(img)
            loop = asyncio.get_running_loop()
            text = await loop.run_in_executor(_OCR_POOL, extract_text_with_paddle, processed)
            docx_bytes = await loop.run_in_executor(_OCR_POOL, build_docx_with_image_and_text, raw, text)
            filename = "ocr_result.docx"
            return StreamingResponse(
                io.BytesIO(docx_bytes),
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        except HTTPException:
            raise
        except Exception as e:
            _ocr_logger.error("OCR /ocr-word failed: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail="OCR-word failed")

# Handlers
from bot.handlers.admin import (
    admin_panel_command, stats_command, broadcast_command,
    handle_admin_text, add_channel_command, remove_channel_command,
    add_premium_command, remove_premium_command, set_limit_command,
    user_info_command, top_users_command, ban_user_command, unban_user_command,
    search_command, support_panel_callback, add_admin_command, remove_admin_command
)

from bot.handlers.admin_middleware import track_user
from bot.handlers.premium_callbacks import premium_callback_handler
from bot.handlers.help import help_command
from bot.handlers.chat_member import chat_member_updated
from bot.handlers.common import balance_handler, help_button_handler
from bot.handlers.feedback import start_feedback, handle_feedback


from bot.handlers.ocr_to_word import (
    ocr_to_word_handler as ocr_handler,
    handle_ocr_image as process_ocr_image,
    process_ocr_tayyor,
)
from bot.handlers.obyektivka import obyektivka_handler, handle_obyektivka_audio as process_obyektivka_audio
from bot.handlers.transliterate import transliterate_handler, process_transliteration as process_transliterate, krill_to_lotin_handler, lotin_to_krill_handler, translit_direction_callback
from bot.handlers.translate import translate_handler, process_translation as process_translate_doc, set_translation_direction
from bot.handlers.image_to_pdf import image_to_pdf_handler, collect_pdf_images as process_image_to_pdf
from bot.handlers.spell_check import spell_check_handler, process_spell_check
from bot.handlers.start import start_command, menu_command
from bot.keyboards.reply_keyboards import get_main_menu, get_back_button, get_more_menu
from bot.utils.i18n import get_regex_for_key, t
from bot.handlers.smart_logic import (
    handle_smart_photo, handle_smart_document, handle_smart_audio, smart_callback_handler
)
from bot.handlers.webapp_data import web_app_data_handler

# Services
from bot.services.settings_service import is_premium
from bot.services.user_service import increment_file_count, get_user_lang

async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    lang = get_user_lang(update.effective_user.id) if update.effective_user else "uz_lat"
    await update.message.reply_text(t("or_menu", lang), reply_markup=get_main_menu(update.effective_user.id if update.effective_user else None, lang))

async def more_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show 'Boshqa xizmatlar' sub-menu"""
    uid = update.effective_user.id if update.effective_user else None
    lang = get_user_lang(uid)
    await update.message.reply_text(t("more_menu_title", lang), reply_markup=get_more_menu(lang))

async def cv_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open CV Resume webapp page via WebApp inline button"""
    from bot.handlers.start import _ACTION_MAP, WEBAPP_BASE
    from telegram import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
    uid = update.effective_user.id if update.effective_user else 0
    lang = get_user_lang(uid)
    page_file, btn_label, desc = _ACTION_MAP["cv"]
    url = f"{WEBAPP_BASE}/{page_file}?telegram_id={uid}&lang={lang}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(btn_label, web_app=WebAppInfo(url=url))]])
    await update.message.reply_text(f"🚀 <b>{desc}</b>", reply_markup=kb, parse_mode="HTML")

async def premium_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💎 **Premium Xizmatlar**\n\n"
        "• Cheklovsiz foydalanish\n"
        "• Reklamasiz\n"
        "• Yuqori tezlik\n"
        "• Kanallarga majburiy a'zolik yo'q\n\n"
        "Sotib olish uchun adminga yozing.",
        parse_mode="Markdown",
        reply_markup=get_back_button()
    )

async def unified_router_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Central check for ban status"""
    if context.user_data.get('is_banned'):
        await update.message.reply_text("🚫 Siz botdan foydalanishdan bloklangansiz.")
        return False
    return True

from bot.handlers.admin import process_admin_state_input

async def handle_router_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await unified_router_check(update, context): return
    if await process_admin_state_input(update, context): return
    
    state = context.user_data.get('waiting_for')
    text = (update.message.text or "").strip().lower()
    
    # 1. State-based routing
    if state == 'ocr_image' and text and 'tayyor' in text:
        if await process_ocr_tayyor(update, context):
            return
        await update.message.reply_text("❌ Hech qanday rasm yuklanmagan. Avval rasmlar yuboring.")
        return
    if state in ['transliterate_text', 'translit_content'] or context.user_data.get('transliterate_direction'):
         await process_transliterate(update, context)
         return
    elif state == 'translate_input' or context.user_data.get('translate_direction'):
         await process_translate_doc(update, context)
         return
    elif state == 'ocr_image' and context.user_data.get('ocr_images') and text and 'tayyor' in text:
         if await process_ocr_tayyor(update, context):
             return
    elif state == 'pdf_images':
         await process_image_to_pdf(update, context)
         return
    elif state == 'feedback':
         await handle_feedback(update, context)
         return

    # 2. NLP / Keyword Routing
    import re
    # Obyektivka (obyektivga, obyektovka, obyektvka, abyektiv)
    uid = update.effective_user.id
    lang = get_user_lang(uid)
    if re.search(r'(obyektiv|obyektov|abyektiv|obekt|resume|rezume|sivi|ma\'lumotnoma)', text):
        await update.message.reply_text(t("opening_service", lang, service="Obyektivka"))
        await obyektivka_handler(update, context)
        return

    # OCR / Word (docx, doc, dox, vord, ocr, textga)
    elif re.search(r'(ocr|word|vord|docx|doc|dox|matn|textga|oqib ber)', text) or (('rasm' in text or 'skan' in text) and ('o\'qi' in text or 'qil' in text)):
        await update.message.reply_text(t("opening_service", lang, service="Rasm -> Word"))
        await ocr_handler(update, context)
        return

    # Image 2 PDF (rasm... pdf)
    elif 'pdf' in text and ('rasm' in text or 'qo\'sh' in text or 'birlash' in text):
        await update.message.reply_text(t("opening_service", lang, service="Rasm -> PDF"))
        await image_to_pdf_handler(update, context)
        return

    # Translate (tarjima, pervod, perevod, translate)
    elif re.search(r'(tarjima|perevod|pervod|translate|tarjma|o\'gir)', text):
        await update.message.reply_text(t("opening_service", lang, service="Tarjima"))
        await translate_handler(update, context)
        return
    
    # Spell Check (imlo, xato, grammatika)
    elif re.search(r'(imlo|xato|tekshir|grammatika)', text):
        await update.message.reply_text(t("opening_service", lang, service="Imlo tekshirish"))
        await spell_check_handler(update, context)
        return

    # 3. Fallback
    await update.message.reply_text(t("unknown_cmd", lang), reply_markup=get_main_menu(uid, lang))

async def handle_router_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await unified_router_check(update, context): return
    if await process_admin_state_input(update, context): return
    
    state = context.user_data.get('waiting_for')
    transliterate_dir = context.user_data.get('transliterate_direction')
    translate_dir = context.user_data.get('translate_direction')  # e.g. 'ru_uz', 'uz_en'
    uid = update.effective_user.id
    
    # Transliterate mode
    if state == 'translit_content' or transliterate_dir:
        await process_transliterate(update, context)
        return
    # Translate mode — detected by presence of translate_direction key
    elif translate_dir or state == 'translate_input':
        await process_translate_doc(update, context)
        increment_file_count(uid, "Translate Doc")
    elif state == 'spell_check_doc' or state == 'spellcheck_file':
        await process_spell_check(update, context)
        increment_file_count(uid, "Spell Check")
    elif state == 'ocr_image' or state == 'ocr_image_doc':
        # Some users send images as documents
        await process_ocr_image(update, context)
        increment_file_count(uid, "OCR Doc-Image")
    elif state == 'feedback':
        await handle_feedback(update, context)
    else:
        # Smart Logic
        await handle_smart_document(update, context)

async def handle_router_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await unified_router_check(update, context): return
    if await process_admin_state_input(update, context): return
    
    state = context.user_data.get('waiting_for')
    uid = update.effective_user.id
    
    if state == 'ocr_image':
        await process_ocr_image(update, context)
        increment_file_count(uid, "OCR Image")
    elif state == 'pdf_images':
        await process_image_to_pdf(update, context)
        increment_file_count(uid, "Image to PDF")
    elif state == 'feedback':
        await handle_feedback(update, context)
    else:
        # Smart Logic (Photo)
        await handle_smart_photo(update, context)

async def handle_router_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await unified_router_check(update, context): return
    if await process_admin_state_input(update, context): return
    
    state = context.user_data.get('waiting_for')
    uid = update.effective_user.id
    
    if state == 'obyektivka_audio':
        await process_obyektivka_audio(update, context)
        increment_file_count(uid, "Obyektivka Audio")
    elif state == 'feedback':
        await handle_feedback(update, context)
    else:
        # Smart logic handles unknown audio
        await handle_smart_audio(update, context)

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await unified_router_check(update, context): return
    
    query = update.callback_query
    await query.answer()
    
    if query.data == "check_subs":
        user_id = query.from_user.id
        
        if is_premium(user_id):
            await query.message.delete()
            await query.message.reply_text("✅ Premium hisob: Obuna shart emas!", reply_markup=get_main_menu())
            return
            
        # ... rest of logic ...
        await query.message.delete()
        await query.message.reply_text("✅ Rahmat!", reply_markup=get_main_menu())


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

async def _webapp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
    """Generic handler: sends inline button opening the correct webapp page."""
    from bot.handlers.start import _ACTION_MAP, WEBAPP_BASE
    from bot.services.user_service import get_user_lang
    uid = update.effective_user.id if update.effective_user else 0
    lang = get_user_lang(uid)
    page_info = _ACTION_MAP.get(action)
    if not page_info:
        await update.message.reply_text("❌ Noma'lum buyruq.") # Or t("unknown_cmd", lang)
        return
    page_file, btn_label, desc = page_info
    from telegram import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
    url = f"{WEBAPP_BASE}/{page_file}?telegram_id={uid}&lang={lang}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(btn_label, web_app=WebAppInfo(url=url))]])
    await update.message.reply_text(f"🚀 <b>{desc}</b>", reply_markup=kb, parse_mode="HTML")

async def cmd_cv(u, c):        await _webapp_cmd(u, c, "cv")
async def cmd_obyektivka(u,c): await _webapp_cmd(u, c, "obyektivka")
async def cmd_ocr(u, c):       await _webapp_cmd(u, c, "ocr")
async def cmd_pdf(u, c):       await _webapp_cmd(u, c, "pdf")
async def cmd_translit(u, c):  await _webapp_cmd(u, c, "translit")
async def cmd_translate(u, c): await _webapp_cmd(u, c, "translate")
async def cmd_premium(u, c):   await _webapp_cmd(u, c, "premium")


def setup_application():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing!")
        return None

    application = ApplicationBuilder().token(BOT_TOKEN).connection_pool_size(8).build()
    
    # 1. CRM Middleware (Tracks + Checks Ban)
    application.add_handler(TypeHandler(Update, track_user), group=-1)

    # 2. Core Commands
    application.add_handler(CommandHandler("start",       start_command))
    application.add_handler(CommandHandler("menu",        menu_command))
    application.add_handler(CommandHandler("help",        help_command))
    # ── Feature shortcut commands (open the matching webapp page directly) ──
    application.add_handler(CommandHandler("cv",          cmd_cv))
    application.add_handler(CommandHandler("obyektivka",  cmd_obyektivka))
    application.add_handler(CommandHandler("ocr",         cmd_ocr))
    application.add_handler(CommandHandler("pdf",         cmd_pdf))
    application.add_handler(CommandHandler("translit",    cmd_translit))
    application.add_handler(CommandHandler("translate",   cmd_translate))
    application.add_handler(CommandHandler("premium",     cmd_premium))

    # Track bot block/unblock
    application.add_handler(ChatMemberHandler(chat_member_updated, ChatMemberHandler.MY_CHAT_MEMBER))
    
    # Admin Commands
    application.add_handler(CommandHandler("admin", admin_panel_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("send", broadcast_command))
    application.add_handler(CommandHandler("user_info", user_info_command))
    application.add_handler(CommandHandler("users", user_info_command)) 
    application.add_handler(CommandHandler("top", top_users_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("ban", ban_user_command))
    application.add_handler(CommandHandler("unban", unban_user_command))
    
    application.add_handler(CommandHandler("add_channel", add_channel_command))
    application.add_handler(CommandHandler("remove_channel", remove_channel_command))
    application.add_handler(CommandHandler("add_premium", add_premium_command))
    application.add_handler(CommandHandler("remove_premium", remove_premium_command))
    application.add_handler(CommandHandler("set_limit", set_limit_command))
    application.add_handler(CommandHandler("add_admin", add_admin_command))
    application.add_handler(CommandHandler("remove_admin", remove_admin_command))

    # 3. Callback Queries
    application.add_handler(CallbackQueryHandler(
        premium_callback_handler,
        pattern="^prem_"
    ))
    
    # Language callback handler removed — bot uses Uzbek by default
    
    application.add_handler(CallbackQueryHandler(smart_callback_handler, pattern="^smart_"))
    application.add_handler(CallbackQueryHandler(translit_direction_callback, pattern="^trl_"))
    application.add_handler(CallbackQueryHandler(support_panel_callback, pattern="^support_"))
    application.add_handler(CallbackQueryHandler(button_callback_handler))

    # 4. Text Menu Navigation — Asosiy tugmalar
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("back_to_menu")), back_to_main_menu))
    application.add_handler(MessageHandler(filters.Regex("^(🔙 Orqaga|🔙 Назад|🔙 Back|🔙 Оркага)$"), back_to_main_menu))
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_more")), more_menu_handler))
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_cv")), cv_handler))
    
    admin_buttons = "^(📊 Statistika|📨 Xabar yuborish|📢 Kanallar|💎 Premium Boshqaruv|⚙️ Sozlamalar|👥 Foydalanuvchilar|➕ Admin qo'shish|❌ Admin o'chirish|🆘 Support so'rovlar|🚪 Panelni yopish)$"
    application.add_handler(MessageHandler(filters.Regex(admin_buttons), handle_admin_text))

    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_ocr")), ocr_handler))
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_oby")), obyektivka_handler))
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_translit")), transliterate_handler))
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_translate")), translate_handler))
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_pdf")), image_to_pdf_handler))
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_spell")), spell_check_handler))
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_premium")), premium_info_handler))
    
    application.add_handler(MessageHandler(filters.Regex("^(🔡 Kirill → Lotin|🔡 Кирилл → Лотин)$"), krill_to_lotin_handler))
    application.add_handler(MessageHandler(filters.Regex("^(🔠 Lotin → Kirill|🔠 Лотин → Кирилл)$"), lotin_to_krill_handler))

    async def go_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        direction = "uz_en"
        if "O'zbek → Ingliz" in text: direction = "uz_en"
        elif "Ingliz → O'zbek" in text: direction = "en_uz"
        elif "Rus → O'zbek" in text: direction = "ru_uz"
        elif "O'zbek → Rus" in text: direction = "uz_ru"
        elif "Rus → Ingliz" in text: direction = "ru_en"
        # Clear any stale state before starting new translation session
        context.user_data.pop('waiting_for', None)
        await set_translation_direction(update, context, direction)

    application.add_handler(MessageHandler(
        filters.Regex("(O'zbek → Ingliz|Ingliz → O'zbek|Rus → O'zbek|O'zbek → Rus|Rus → Ingliz)"),
        go_translate
    ))
    
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_balance")), balance_handler))
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_contact")), start_feedback))
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_help")), help_button_handler))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_router_text))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_router_doc))
    application.add_handler(MessageHandler(filters.PHOTO, handle_router_photo))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_router_audio))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))

    async def handle_router_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await unified_router_check(update, context): return
        if await process_admin_state_input(update, context): return
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_router_other))

    application.add_error_handler(error_handler)
    return application

def main():
    application = setup_application()
    if application:
        logger.info("✅ Bot is starting in POLLING mode...")
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
