import os
import time
import logging
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from bot.keyboards.reply_keyboards import get_translate_menu, get_back_button
from bot.services.ai_service import translate_document_gemini

logger = logging.getLogger(__name__)

async def translate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show translation menu"""
    await update.message.reply_text(
        "🌐 **Hujjat Tarjimasi**\n\n"
        "Til yo'nalishini tanlang:",
        reply_markup=get_translate_menu(),
        parse_mode="Markdown"
    )


async def set_translation_direction(update: Update, context: ContextTypes.DEFAULT_TYPE, direction: str):
    """Set translation direction and wait for file"""
    context.user_data['translate_direction'] = direction
    
    direction_map = {
        'uz_en': "O'zbek → Ingliz",
        'en_uz': "Ingliz → O'zbek",
        'ru_uz': "Rus → O'zbek",
        'uz_ru': "O'zbek → Rus",
        'ru_en': "Rus → Ingliz"
    }
    
    await update.message.reply_text(
        f"📄 **{direction_map.get(direction, 'Tarjima')}**\n\n"
        "Hujjat yuboring (DOC, PPT, XLS).",
        reply_markup=get_back_button()
    )


async def process_translation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process file translation with AI"""
    direction = context.user_data.get('translate_direction')
    if not direction:
        return

    # Map direction to standard code
    target_lang = "en"
    if "uz_en" in direction or "ru_en" in direction: target_lang = "en"
    elif "uz_ru" in direction: target_lang = "ru"
    elif "en_uz" in direction or "ru_uz" in direction: target_lang = "uz"

    message = update.message
    if not message.document:
        await message.reply_text("Iltimos, Word (DOCX) fayl yuboring.")
        return
        
    file_name = message.document.file_name
    if not file_name.endswith('.docx'):
        await message.reply_text("❌ Hozircha faqat .DOCX (Word) fayllarni qabul qilaman.")
        return

    status_msg = await message.reply_text(
        f"⏳ '{file_name}' tarjima qilinmoqda...\n"
        "AI ishlamoqda, iltimos kuting (hajmiga qarab 30-60 soniya)."
    )
    
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
    
    
    # Download file
    try:
        file = await message.document.get_file()
        temp_path = f"temp_translate_{message.from_user.id}_{int(time.time())}.docx"
        await file.download_to_drive(temp_path)
        
        # Translate
        translated_path = await translate_document_gemini(temp_path, target_lang)
        
        if translated_path and os.path.exists(translated_path):
            await status_msg.edit_text("✅ Tarjima tayyor! Fayl yuklanmoqda...")
            
            with open(translated_path, "rb") as f:
                output_name = f"Tarjima_{target_lang}_{file_name}"
                await message.reply_document(
                    document=InputFile(f, filename=output_name),
                    caption=f"✅ Tarjima tayyor!\n\nOriginal: {file_name}\nTil: {target_lang.upper()}",
                    reply_markup=get_back_button()
                )
            
            # Cleanup
            try:
                os.remove(translated_path)
            except: pass
            
        else:
            await status_msg.edit_text("❌ Tarjima qilishda xatolik yuz berdi. Fayl formati murakkab bo'lishi mumkin.")
            
        # Cleanup original temp
        if os.path.exists(temp_path):
             os.remove(temp_path)
             
    except Exception as e:
        logger.error(f"Translation Handler Error: {e}", exc_info=True)
        await status_msg.edit_text("❌ Kutilmagan xatolik yuz berdi.")
    context.user_data.pop('translate_direction', None)
