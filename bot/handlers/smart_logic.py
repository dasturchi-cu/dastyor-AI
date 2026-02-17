import logging
import os
import time
from telegram import Update
from telegram.ext import ContextTypes
from bot.keyboards.inline_keyboards import (
    get_smart_photo_keyboard, get_smart_document_keyboard, get_smart_audio_keyboard
)
from bot.handlers.ocr_to_word import perform_ocr_and_send

logger = logging.getLogger(__name__)

async def handle_smart_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Smartly handle photo upload without menu selection"""
    
    # Save file ID temporarily
    file_id = update.message.photo[-1].file_id if update.message.photo else update.message.document.file_id
    context.user_data['smart_file_id'] = file_id
    context.user_data['smart_file_type'] = 'photo'
    
    msg = (
        "🤖 **Aqlli Yordamchi:** Rasm qabul qilindi!\n\n"
        "Nima qilishni xohlaysiz? Quyidagi varianlardan birini tanlang:"
    )
    
    await update.message.reply_text(
        msg, 
        reply_markup=get_smart_photo_keyboard(),
        parse_mode="Markdown"
    )

async def handle_smart_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Smartly handle document upload"""
    
    doc = update.message.document
    file_ext = os.path.splitext(doc.file_name)[1].lower() if doc.file_name else ""
    
    # Save file ID
    context.user_data['smart_file_id'] = doc.file_id
    context.user_data['smart_file_type'] = 'document'
    context.user_data['smart_file_ext'] = file_ext
    context.user_data['smart_file_name'] = doc.file_name
    
    msg = (
        f"🤖 **Aqlli Yordamchi:** Hujjat qabul qilindi (`{doc.file_name}`)!\n\n"
        "Qanday amal bajaramiz?"
    )
    
    await update.message.reply_text(
        msg, 
        reply_markup=get_smart_document_keyboard(file_ext),
        parse_mode="Markdown"
    )

async def handle_smart_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Smartly handle audio/voice upload"""
    
    # Save file ID
    file_id = update.message.voice.file_id if update.message.voice else update.message.audio.file_id
    context.user_data['smart_file_id'] = file_id
    context.user_data['smart_file_type'] = 'audio'
    
    msg = (
        "🤖 **Aqlli Yordamchi:** Audio xabar keldi!\n\n"
        "Uni matnga aylantiraymi yoki obyektivka to'ldiramizmi?"
    )
    
    await update.message.reply_text(
        msg, 
        reply_markup=get_smart_audio_keyboard(),
        parse_mode="Markdown"
    )

async def smart_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from smart keyboards"""
    query = update.callback_query
    data = query.data
    
    # Answer callback
    await query.answer()
    
    if data == "smart_cancel":
        if 'smart_file_id' in context.user_data: del context.user_data['smart_file_id']
        await query.message.edit_text("🚫 Bekor qilindi.")
        return

    # Check if file exists in context
    file_id = context.user_data.get('smart_file_id')
    if not file_id:
        await query.message.edit_text("⚠️ Fayl sessiyasi tugagan. Iltimos, qayta yuboring.")
        return
        
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    temp_path = None
    
    try:
        # 1. OCR (Rasm -> Word)
        if data == "smart_ocr":
            await query.message.edit_text("⏳ Yuklanmoqda...")
            
            # Download file
            file_obj = await context.bot.get_file(file_id)
            temp_path = f"smart_ocr_{user_id}_{int(time.time())}.jpg"
            await file_obj.download_to_drive(temp_path)
            
            # Delete menu message
            await query.message.delete()
            
            # Perform OCR (using shared logic)
            await perform_ocr_and_send(context, temp_path, chat_id, user_id)
            return

        elif data == "smart_translate":
             await query.message.edit_text("🌍 Tarjima funksiyasi tez orada qo'shiladi! (Beta)")
             return
             
        elif data == "smart_img2pdf":
             await query.message.edit_text("🖼 PDF ga qo'shish uchun 'Rasm->PDF' menyusidan foydalaning.")
             return

        # ... other handlers ...
        
        await query.message.edit_text(f"✅ Tanlandi: {data}. (Ishlanmoqda...)")
        
    except Exception as e:
        logger.error(f"Smart Callback Error: {e}", exc_info=True)
        await query.message.edit_text(f"❌ Xatolik: {e}")
        
    finally:
        # Cleanup if temp_path was created and used inside local scope (if passed away, cleanup there)
        # perform_ocr_and_send does NOT delete input file (it takes path).
        # We need to delete it here.
        if temp_path and os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass
