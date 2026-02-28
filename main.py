"""
Main Bot Entry Point (with Ban Check Middleware)
"""
import logging
import os
import asyncio
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

# Handlers
from bot.handlers.admin import (
    admin_panel_command, stats_command, broadcast_command,
    handle_admin_text, add_channel_command, remove_channel_command,
    add_premium_command, remove_premium_command, set_limit_command,
    user_info_command, top_users_command, ban_user_command, unban_user_command,
    search_command
)

from bot.handlers.admin_middleware import track_user
from bot.handlers.premium_callbacks import premium_callback_handler
from bot.handlers.help import help_command
from bot.handlers.chat_member import chat_member_updated
from bot.handlers.common import balance_handler, contact_handler, help_button_handler


from bot.handlers.ocr_to_word import ocr_to_word_handler as ocr_handler, handle_ocr_image as process_ocr_image
from bot.handlers.obyektivka import obyektivka_handler, handle_obyektivka_audio as process_obyektivka_audio
from bot.handlers.transliterate import transliterate_handler, process_transliteration as process_transliterate, krill_to_lotin_handler, lotin_to_krill_handler
from bot.handlers.translate import translate_handler, process_translation as process_translate_doc, set_translation_direction
from bot.handlers.image_to_pdf import image_to_pdf_handler, collect_pdf_images as process_image_to_pdf
from bot.handlers.spell_check import spell_check_handler, process_spell_check
from bot.handlers.start import start_command, menu_command
from bot.keyboards.reply_keyboards import get_main_menu, get_back_button
from bot.handlers.smart_logic import (
    handle_smart_photo, handle_smart_document, handle_smart_audio, smart_callback_handler
)

# Services
from bot.services.usage_tracker import can_use as check_usage_limit, increment_usage
from bot.services.settings_service import is_premium
from bot.services.user_service import increment_file_count, is_user_banned

async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("🏠 Bosh menyu", reply_markup=get_main_menu())

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

async def check_ban_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Checks if user is banned before ANY interaction"""
    if update.effective_user:
        if is_user_banned(update.effective_user.id):
             # You can notify them or silently ignore
             # await update.message.reply_text("🚫 Siz bloklangansiz.")
             # Stop processing
             raise Exception("User Banned") # A bit harsh, but stops propagation efficiently in py-telegram-bot logic if we wrap it?
             # Actually, better to just return True/False and use logic in router?
             # But 'TypeHandler' runs parallel usually. 
             pass

# Instead of complex middleware blocking, let's add a check at the start of routers.
# Or better: track_user sets a flag.

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
    text = update.message.text.lower()
    
    # 1. State-based routing
    if state == 'transliterate_text' or context.user_data.get('transliterate_direction'):
         await process_transliterate(update, context)
         increment_file_count(update.effective_user.id, "Transliterate Text")
         return
    elif state == 'pdf_images':
         await process_image_to_pdf(update, context)
         return

    # 2. NLP / Keyword Routing
    # 2. NLP / Keyword Routing
    import re
    # Obyektivka (obyektivga, obyektovka, obyektvka, abyektiv)
    if re.search(r'(obyektiv|obyektov|abyektiv|obekt|resume|rezume|sivi|ma\'lumotnoma)', text):
        await update.message.reply_text("🤖 Tushundim! **Obyektivka** xizmatini ochyapman...")
        await obyektivka_handler(update, context)
        return

    # OCR / Word (docx, doc, dox, vord, ocr, textga)
    elif re.search(r'(ocr|word|vord|docx|doc|dox|matn|textga|oqib ber)', text) or (('rasm' in text or 'skan' in text) and ('o\'qi' in text or 'qil' in text)):
        await update.message.reply_text("🤖 Tushundim! **Rasm -> Word** xizmatini ochyapman...")
        await ocr_handler(update, context)
        return

    # Image 2 PDF (rasm... pdf)
    elif 'pdf' in text and ('rasm' in text or 'qo\'sh' in text or 'birlash' in text):
        await update.message.reply_text("🤖 Tushundim! **Rasm -> PDF** xizmatini ochyapman...")
        await image_to_pdf_handler(update, context)
        return

    # Translate (tarjima, pervod, perevod, translate)
    elif re.search(r'(tarjima|perevod|pervod|translate|tarjma|o\'gir)', text):
        await update.message.reply_text("🤖 Tushundim! **Tarjima** xizmatini ochyapman...")
        await translate_handler(update, context)
        return
    
    # Spell Check (imlo, xato, grammatika)
    elif re.search(r'(imlo|xato|tekshir|grammatika)', text):
        await update.message.reply_text("🤖 Tushundim! **Imlo tekshirish** xizmatini ochyapman...")
        await spell_check_handler(update, context)
        return

    # 3. Fallback
    await update.message.reply_text("❓ Tushunmadim. Menyudan bo'lim tanlang yoki aniqroq yozing.", reply_markup=get_main_menu())

async def handle_router_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await unified_router_check(update, context): return
    if await process_admin_state_input(update, context): return
    
    state = context.user_data.get('waiting_for')
    uid = update.effective_user.id
    
    if state == 'doc_transliterate' or context.user_data.get('transliterate_direction'):
        await process_transliterate(update, context)
        increment_file_count(uid, "Transliterate Doc")
    elif context.user_data.get('translate_direction'):
        await process_translate_doc(update, context)
        increment_file_count(uid, "Translate Doc")
    elif state == 'spell_check_doc':
        await process_spell_check(update, context)
        increment_file_count(uid, "Spell Check")
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
    else:
        # Smart Logic
        await handle_smart_photo(update, context)

async def handle_router_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await unified_router_check(update, context): return
    if await process_admin_state_input(update, context): return
    
    state = context.user_data.get('waiting_for')
    uid = update.effective_user.id
    
    if state == 'obyektivka_audio':
        await process_obyektivka_audio(update, context)
        increment_file_count(uid, "Obyektivka Audio")
    else:
        # Smart logic handles unknown audio
        await handle_smart_audio(update, context)

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await unified_router_check(update, context): return
    
    query = update.callback_query
    await query.answer()
    
    if query.data == "check_subs":
        from bot.services.settings_service import get_channels
        channels = get_channels()
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

def setup_application():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing!")
        return None

    application = ApplicationBuilder().token(BOT_TOKEN).connection_pool_size(8).build()
    
    # 1. CRM Middleware (Tracks + Checks Ban)
    application.add_handler(TypeHandler(Update, track_user), group=-1)

    # 2. Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("help", help_command))

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

    # 3. Callback Queries
    application.add_handler(CallbackQueryHandler(
        premium_callback_handler,
        pattern="^prem_"
    ))
    application.add_handler(CallbackQueryHandler(smart_callback_handler, pattern="^smart_"))
    application.add_handler(CallbackQueryHandler(button_callback_handler))

    # 4. Text Menu Navigation
    application.add_handler(MessageHandler(filters.Regex("^🔙 Orqaga$"), back_to_main_menu))
    
    admin_buttons = "^(📊 Statistika|📨 Xabar yuborish|📢 Kanallar|💎 Premium Boshqaruv|⚙️ Sozlamalar|👥 Foydalanuvchilar|🚪 Panelni yopish)$"
    application.add_handler(MessageHandler(filters.Regex(admin_buttons), handle_admin_text))

    application.add_handler(MessageHandler(filters.Regex("^📄 Rasm→Word AI$"), ocr_handler))
    application.add_handler(MessageHandler(filters.Regex("^📋 Obyektivka AI$"), obyektivka_handler))
    application.add_handler(MessageHandler(filters.Regex("^🔤 Krill-Lotin$"), transliterate_handler))
    application.add_handler(MessageHandler(filters.Regex("^🌐 Tarjima fayl$"), translate_handler))
    application.add_handler(MessageHandler(filters.Regex("^🖼 Rasm→PDF$"), image_to_pdf_handler))
    application.add_handler(MessageHandler(filters.Regex("^✏️ Imlo tekshirish$"), spell_check_handler))
    application.add_handler(MessageHandler(filters.Regex("^💎 Premium xizmatlar$"), premium_info_handler))
    
    application.add_handler(MessageHandler(filters.Regex("^🔡 Kirill → Lotin$"), krill_to_lotin_handler))
    application.add_handler(MessageHandler(filters.Regex("^🔠 Lotin → Kirill$"), lotin_to_krill_handler))

    async def go_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        direction = "uz_en"
        if "O'zbek → Ingliz" in text: direction = "uz_en"
        elif "Ingliz → O'zbek" in text: direction = "en_uz"
        elif "Rus → O'zbek" in text: direction = "ru_uz"
        elif "O'zbek → Rus" in text: direction = "uz_ru"
        elif "Rus → Ingliz" in text: direction = "ru_en"
        await set_translation_direction(update, context, direction)

    application.add_handler(MessageHandler(
        filters.Regex("(O'zbek → Ingliz|Ingliz → O'zbek|Rus → O'zbek|O'zbek → Rus|Rus → Ingliz)"),
        go_translate
    ))
    
    application.add_handler(MessageHandler(filters.Regex("^💰 Balans$"), balance_handler))
    application.add_handler(MessageHandler(filters.Regex("^Aloqa ✉️$"), contact_handler))
    application.add_handler(MessageHandler(filters.Regex("^🆘 Yordam$"), help_button_handler))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_router_text))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_router_doc))
    application.add_handler(MessageHandler(filters.PHOTO, handle_router_photo))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_router_audio))

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
