"""
Main Bot Entry Point (with Ban Check Middleware).

OCR / WebApp HTTP API: run `uvicorn api_webhook:app` (or `uvicorn backend.app:app`).
"""
import os

# ── Paddle / PaddleOCR stability flags (handlers may load OCR lazily) ─────
os.environ.setdefault("FLAGS_enable_pir_api", "0")
os.environ.setdefault("FLAGS_use_new_executor", "0")
os.environ.setdefault("FLAGS_enable_onednn", "0")
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_enable_pir_in_executor", "0")

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    filters, ContextTypes, TypeHandler, CallbackQueryHandler, ChatMemberHandler
)

try:
    load_dotenv()
except Exception:
    # dotenv is optional; never crash the bot for it
    pass

try:
    from backend.sentry_init import init_sentry

    init_sentry(service_name="bot")
except Exception:
    pass

from config import BOT_TOKEN, logger

# Handlers
from bot.handlers.admin import (
    admin_panel_command, stats_command, broadcast_command,
    handle_admin_text, add_channel_command, remove_channel_command,
    add_premium_command, remove_premium_command, set_limit_command,
    user_info_command, top_users_command, ban_user_command, unban_user_command,
    search_command, support_panel_callback, add_admin_command, remove_admin_command,
    approve_premium_command, maintenance_on_command, maintenance_off_command,
    maintenance_status_command
)

from bot.handlers.admin_middleware import track_user
from bot.handlers.premium_callbacks import premium_callback_handler
from bot.handlers.premium import (
    premium_handler,
    premium_purchase_callback,
    handle_premium_screenshot,
    premium_payment_review_callback,
)
from bot.handlers.help import help_command
from bot.handlers.chat_member import chat_member_updated
from bot.handlers.common import balance_handler, help_button_handler
from bot.handlers.feedback import start_feedback, handle_feedback
from bot.handlers.support_group import support_group_router, SUPPORT_GROUP_ID


from bot.handlers.ocr_to_word import (
    ocr_to_word_handler as ocr_handler,
    handle_ocr_image as process_ocr_image,
    process_ocr_tayyor,
)
from bot.handlers.obyektivka import (
    auto_voice_obyektivka_from_message,
    obyektivka_handler,
    handle_obyektivka_audio as process_obyektivka_audio,
)
from bot.handlers.transliterate import transliterate_handler, process_transliteration as process_transliterate, krill_to_lotin_handler, lotin_to_krill_handler, translit_direction_callback
from bot.handlers.translate import translate_handler, process_translation as process_translate_doc, set_translation_direction
from bot.handlers.image_to_pdf import image_to_pdf_handler, collect_pdf_images as process_image_to_pdf
from bot.handlers.spell_check import spell_check_handler, process_spell_check
from bot.handlers.start import start_command, menu_command
from bot.keyboards.reply_keyboards import get_main_menu, get_back_button, get_more_menu
from bot.utils.i18n import get_regex_for_key, t
from bot.handlers.smart_logic import (
    handle_smart_photo, handle_smart_document, smart_callback_handler
)
from bot.handlers.webapp_data import web_app_data_handler

# Services
from bot.services.settings_service import is_premium
from bot.services.settings_service import get_maintenance_mode
from bot.handlers.start import DEFAULT_LANG
from bot.services.admin_service import is_admin as is_admin_user
from bot.utils.system_tracker import track_span


def _span_meta(update: Update) -> dict:
    md: dict = {}
    try:
        if update and getattr(update, "effective_chat", None):
            md["chat_id"] = getattr(update.effective_chat, "id", None)
            md["chat_type"] = getattr(update.effective_chat, "type", None)
        if update and getattr(update, "effective_message", None):
            md["message_id"] = getattr(update.effective_message, "message_id", None)
        if update and getattr(update, "callback_query", None) and update.callback_query:
            md["callback_data"] = (str(update.callback_query.data or "")[:180]) or None
    except Exception:
        pass
    return md


def spanify(action_name: str, fn):
    """
    Wrap a PTB handler to emit START/END/ERROR spans into system_logs.
    Does not change behavior: exceptions still propagate to PTB error_handler.
    """

    async def _wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        uid = None
        uname = None
        try:
            if update and update.effective_user:
                uid = int(update.effective_user.id)
                uname = update.effective_user.username
        except Exception:
            pass
        async with track_span(
            telegram_id=uid,
            username=uname,
            action_name=action_name,
            metadata=_span_meta(update),
        ):
            return await fn(update, context, *args, **kwargs)

    return _wrapped

async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type != "private":
        return
    context.user_data.clear()
    lang = DEFAULT_LANG

    # Instant UX: send a tiny ack, then render menu in background.
    ack_mid = None
    try:
        ack = await update.message.reply_text("⏳ ...")
        ack_mid = getattr(ack, "message_id", None)
    except Exception:
        pass

    async def _delete_ack_later(chat_id: int, ack_message_id: int | None, delay_s: float):
        if not ack_message_id:
            return
        try:
            await asyncio.sleep(delay_s)
            await context.bot.delete_message(chat_id=chat_id, message_id=int(ack_message_id))
        except Exception:
            pass

    async def _send_menu_bg(chat_id: int, ack_message_id: int | None):
        try:
            uid = update.effective_user.id if update.effective_user else None
            await context.bot.send_message(
                chat_id=chat_id,
                text=t("or_menu", lang),
                reply_markup=get_main_menu(uid, lang),
            )
        finally:
            try:
                if ack_message_id:
                    await context.bot.delete_message(chat_id=chat_id, message_id=int(ack_message_id))
            except Exception:
                pass

    try:
        chat_id = int(update.effective_chat.id)
        asyncio.create_task(_send_menu_bg(chat_id, ack_mid))
        # Fallback: if delete fails in bg flow, remove after a short delay anyway.
        asyncio.create_task(_delete_ack_later(chat_id, ack_mid, 5.0))
    except Exception:
        # Fallback: if task can't be created, do the normal slow send
        await update.message.reply_text(
            t("or_menu", lang),
            reply_markup=get_main_menu(update.effective_user.id if update.effective_user else None, lang),
        )

async def more_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show 'Boshqa xizmatlar' sub-menu"""
    if not update.effective_chat or update.effective_chat.type != "private":
        return
    await update.message.reply_text(t("more_menu_title", DEFAULT_LANG), reply_markup=get_more_menu(DEFAULT_LANG))

async def cv_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open CV Resume webapp page via WebApp inline button"""
    if not update.effective_chat or update.effective_chat.type != "private":
        return
    from bot.handlers.start import _ACTION_MAP, WEBAPP_BASE
    from telegram import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
    uid = update.effective_user.id if update.effective_user else 0
    page_file, btn_label, desc = _ACTION_MAP["cv"]
    url = f"{WEBAPP_BASE}/{page_file}?telegram_id={uid}&lang={DEFAULT_LANG}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(btn_label, web_app=WebAppInfo(url=url))]])
    await update.message.reply_text(f"🚀 <b>{desc}</b>", reply_markup=kb, parse_mode="HTML")

async def premium_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await premium_handler(update, context)

async def unified_router_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Central check for ban status"""
    if context.user_data.get('is_banned'):
        await update.message.reply_text("🚫 Siz botdan foydalanishdan bloklangansiz.")
        return False
    # Maintenance mode: allow only admins to use the bot.
    uid = update.effective_user.id if update.effective_user else None
    if uid:
        if get_maintenance_mode() and not is_admin_user(uid):
            await update.message.reply_text(
                "🛠 Botda texnik ishlar ketmoqda. Iltimos, birozdan keyin qayta urinib ko'ring."
            )
            return False
    return True

from bot.handlers.admin import process_admin_state_input

async def handle_router_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type != "private":
        return
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
    elif state == 'spell_check_doc' or state == 'spellcheck_file':
         await process_spell_check(update, context)
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
    lang = DEFAULT_LANG
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
    if not update.effective_chat or update.effective_chat.type != "private":
        return
    if not await unified_router_check(update, context): return
    if await handle_premium_screenshot(update, context):
        return
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
    elif state == 'spell_check_doc' or state == 'spellcheck_file':
        await process_spell_check(update, context)
    elif state == 'ocr_image' or state == 'ocr_image_doc':
        # Some users send images as documents
        await process_ocr_image(update, context)
    elif state == 'feedback':
        await handle_feedback(update, context)
    else:
        # Smart Logic
        await handle_smart_document(update, context)

async def handle_router_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type != "private":
        return
    if not await unified_router_check(update, context): return
    if await handle_premium_screenshot(update, context):
        return
    if await process_admin_state_input(update, context): return
    
    state = context.user_data.get('waiting_for')

    if state == 'ocr_image':
        await process_ocr_image(update, context)
    elif state == 'pdf_images':
        await process_image_to_pdf(update, context)
    elif state == 'feedback':
        await handle_feedback(update, context)
    else:
        # Smart Logic (Photo)
        await handle_smart_photo(update, context)

async def handle_router_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type != "private":
        return
    if not await unified_router_check(update, context): return
    if await process_admin_state_input(update, context): return
    
    state = context.user_data.get('waiting_for')

    if state == 'obyektivka_audio':
        await process_obyektivka_audio(update, context)
    elif state == 'feedback':
        await handle_feedback(update, context)
    else:
        await auto_voice_obyektivka_from_message(update, context)

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
    # Fire-and-forget telemetry to Supabase logs (if available)
    try:
        from bot.utils.action_logger import log_action_fire_and_forget

        uid = None
        uname = None
        if isinstance(update, Update) and update.effective_user:
            uid = update.effective_user.id
            uname = update.effective_user.username
        if uid:
            log_action_fire_and_forget(
                telegram_id=int(uid),
                username=uname,
                action_type="ERROR",
                details="bot:update_handler",
                metadata={
                    "error": str(getattr(context, "error", "") or "")[:500],
                    "update_type": type(update).__name__,
                },
            )
    except Exception:
        pass

async def _webapp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
    """Generic handler: sends inline button opening the correct webapp page."""
    if not update.effective_chat or update.effective_chat.type != "private":
        return
    from bot.handlers.start import _ACTION_MAP, WEBAPP_BASE
    uid = update.effective_user.id if update.effective_user else 0
    lang = DEFAULT_LANG
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
async def cmd_premium(u, c):   await premium_handler(u, c)


def setup_application():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing!")
        return None

    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connection_pool_size(int(__import__("os").getenv("PTB_POOL_SIZE", "20") or "20"))
        .pool_timeout(30.0)
        .build()
    )
    
    # 1. CRM Middleware (Tracks + Checks Ban)
    application.add_handler(TypeHandler(Update, track_user), group=-1)
    # 1.1 Support group strict router (ignore all other bot features there)
    application.add_handler(
        MessageHandler(filters.Chat(chat_id=SUPPORT_GROUP_ID), spanify("bot:support_group_router", support_group_router)),
        group=0,
    )

    # 2. Core Commands
    application.add_handler(CommandHandler("start",       spanify("bot:cmd_start", start_command)))
    application.add_handler(CommandHandler("menu",        spanify("bot:cmd_menu", menu_command)))
    application.add_handler(CommandHandler("help",        spanify("bot:cmd_help", help_command)))
    # ── Feature shortcut commands (open the matching webapp page directly) ──
    application.add_handler(CommandHandler("cv",          spanify("bot:cmd_cv", cmd_cv)))
    application.add_handler(CommandHandler("obyektivka",  spanify("bot:cmd_obyektivka", cmd_obyektivka)))
    application.add_handler(CommandHandler("ocr",         spanify("bot:cmd_ocr", cmd_ocr)))
    application.add_handler(CommandHandler("pdf",         spanify("bot:cmd_pdf", cmd_pdf)))
    application.add_handler(CommandHandler("translit",    spanify("bot:cmd_translit", cmd_translit)))
    application.add_handler(CommandHandler("translate",   spanify("bot:cmd_translate", cmd_translate)))
    application.add_handler(CommandHandler("premium",     spanify("bot:cmd_premium", cmd_premium)))

    # Track bot block/unblock
    application.add_handler(
        ChatMemberHandler(spanify("bot:chat_member_updated", chat_member_updated), ChatMemberHandler.MY_CHAT_MEMBER)
    )
    
    # Admin Commands
    application.add_handler(CommandHandler("admin", spanify("bot:cmd_admin", admin_panel_command)))
    application.add_handler(CommandHandler("stats", spanify("bot:cmd_stats", stats_command)))
    application.add_handler(CommandHandler("send", spanify("bot:cmd_send", broadcast_command)))
    application.add_handler(CommandHandler("user_info", spanify("bot:cmd_user_info", user_info_command)))
    application.add_handler(CommandHandler("users", spanify("bot:cmd_users", user_info_command)))
    application.add_handler(CommandHandler("top", spanify("bot:cmd_top", top_users_command)))
    application.add_handler(CommandHandler("search", spanify("bot:cmd_search", search_command)))
    application.add_handler(CommandHandler("ban", spanify("bot:cmd_ban", ban_user_command)))
    application.add_handler(CommandHandler("unban", spanify("bot:cmd_unban", unban_user_command)))
    
    application.add_handler(CommandHandler("add_channel", spanify("bot:cmd_add_channel", add_channel_command)))
    application.add_handler(CommandHandler("remove_channel", spanify("bot:cmd_remove_channel", remove_channel_command)))
    application.add_handler(CommandHandler("add_premium", spanify("bot:cmd_add_premium", add_premium_command)))
    application.add_handler(CommandHandler("remove_premium", spanify("bot:cmd_remove_premium", remove_premium_command)))
    application.add_handler(CommandHandler("approve", spanify("bot:cmd_approve", approve_premium_command)))
    application.add_handler(CommandHandler("maintenance_on", spanify("bot:cmd_maintenance_on", maintenance_on_command)))
    application.add_handler(CommandHandler("maintenance_off", spanify("bot:cmd_maintenance_off", maintenance_off_command)))
    application.add_handler(CommandHandler("maintenance_status", spanify("bot:cmd_maintenance_status", maintenance_status_command)))
    application.add_handler(CommandHandler("set_limit", spanify("bot:cmd_set_limit", set_limit_command)))
    application.add_handler(CommandHandler("add_admin", spanify("bot:cmd_add_admin", add_admin_command)))
    application.add_handler(CommandHandler("remove_admin", spanify("bot:cmd_remove_admin", remove_admin_command)))

    # 3. Callback Queries
    application.add_handler(CallbackQueryHandler(
        spanify("bot:cb_premium", premium_callback_handler),
        pattern="^prem_"
    ))
    application.add_handler(CallbackQueryHandler(
        spanify("bot:cb_premium_buy", premium_purchase_callback),
        pattern="^buy_"
    ))
    application.add_handler(CallbackQueryHandler(
        spanify("bot:cb_premium_review", premium_payment_review_callback),
        pattern=r"^prempay_(approve|reject)_\d+$"
    ))
    
    # Language callback handler removed — bot uses Uzbek by default
    
    application.add_handler(CallbackQueryHandler(spanify("bot:cb_smart", smart_callback_handler), pattern="^smart_"))
    application.add_handler(CallbackQueryHandler(spanify("bot:cb_translit_dir", translit_direction_callback), pattern="^trl_"))
    application.add_handler(CallbackQueryHandler(spanify("bot:cb_support_panel", support_panel_callback), pattern="^support_"))
    application.add_handler(CallbackQueryHandler(spanify("bot:cb_default", button_callback_handler)))

    # 4. Text Menu Navigation — Asosiy tugmalar
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("back_to_menu")), spanify("bot:ui_back_to_menu", back_to_main_menu)))
    application.add_handler(MessageHandler(filters.Regex("^(🔙 Orqaga|🔙 Назад|🔙 Back|🔙 Оркага)$"), spanify("bot:ui_back_to_menu2", back_to_main_menu)))
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_more")) & filters.ChatType.PRIVATE, spanify("bot:ui_more_menu", more_menu_handler)))
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_cv")) & filters.ChatType.PRIVATE, spanify("bot:ui_open_cv", cv_handler)))
    
    admin_buttons = "^(📊 Statistika|📨 Xabar yuborish|📢 Kanallar|💎 Premium Boshqaruv|⚙️ Sozlamalar|👥 Foydalanuvchilar|➕ Admin qo'shish|❌ Admin o'chirish|🆘 Support so'rovlar|🚪 Panelni yopish)$"
    application.add_handler(MessageHandler(filters.Regex(admin_buttons), spanify("bot:admin_text", handle_admin_text)))

    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_ocr")), spanify("bot:ui_ocr", ocr_handler)))
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_oby")) & filters.ChatType.PRIVATE, spanify("bot:ui_obyektivka", obyektivka_handler)))
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_translit")), spanify("bot:ui_translit", transliterate_handler)))
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_translate")), spanify("bot:ui_translate", translate_handler)))
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_pdf")), spanify("bot:ui_pdf", image_to_pdf_handler)))
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_spell")), spanify("bot:ui_spellcheck", spell_check_handler)))
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_premium")) & filters.ChatType.PRIVATE, spanify("bot:ui_premium", premium_info_handler)))
    application.add_handler(MessageHandler(filters.Regex("^Premium sotib olish$") & filters.ChatType.PRIVATE, spanify("bot:ui_premium2", premium_info_handler)))
    
    application.add_handler(MessageHandler(filters.Regex("^(🔡 Kirill → Lotin|🔡 Кирилл → Лотин)$"), spanify("bot:ui_kirill_to_lotin", krill_to_lotin_handler)))
    application.add_handler(MessageHandler(filters.Regex("^(🔠 Lotin → Kirill|🔠 Лотин → Кирилл)$"), spanify("bot:ui_lotin_to_kirill", lotin_to_krill_handler)))

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
        spanify("bot:ui_translate_direction", go_translate)
    ))
    
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_balance")) & filters.ChatType.PRIVATE, spanify("bot:ui_balance", balance_handler)))
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_contact")), spanify("bot:ui_contact", start_feedback)))
    application.add_handler(MessageHandler(filters.Regex(get_regex_for_key("btn_help")), spanify("bot:ui_help", help_button_handler)))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, spanify("bot:router_text", handle_router_text)))
    application.add_handler(MessageHandler(filters.Document.ALL, spanify("bot:router_doc", handle_router_doc)))
    application.add_handler(MessageHandler(filters.PHOTO, spanify("bot:router_photo", handle_router_photo)))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, spanify("bot:router_audio", handle_router_audio)))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, spanify("bot:web_app_data", web_app_data_handler)))

    async def handle_router_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await unified_router_check(update, context): return
        if await process_admin_state_input(update, context): return
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, spanify("bot:router_other", handle_router_other)))

    application.add_error_handler(error_handler)
    return application

def main():
    application = setup_application()
    if application:
        logger.info("✅ Bot is starting in POLLING mode...")
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
