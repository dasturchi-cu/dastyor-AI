"""
Imlo Tekshirish (Spell Check) Handler
Uses ai_service to check spelling asynchronously.
Supports both .docx and .pptx files.
"""
import os
import time
import logging
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from bot.keyboards.reply_keyboards import get_back_button
from bot.services.ai_service import check_spelling_gemini, check_spelling_pptx

logger = logging.getLogger(__name__)

SUPPORTED_EXTS = ('.docx', '.pptx')


async def spell_check_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle spell check request"""
    await update.message.reply_text(
        "✅ **Imlo Tekshirish**\n\n"
        "Word (.docx) yoki PowerPoint (.pptx) hujjat yuboring.\n"
        "AI imlo xatolarini aniqlaydi va tuzatilgan faylni qaytaradi.\n\n"
        "💡 Hozircha o'zbek va rus tillarini qo'llab-quvvatlaydi.",
        reply_markup=get_back_button(),
        parse_mode="Markdown"
    )
    context.user_data['waiting_for'] = 'spell_check_doc'


async def process_spell_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process spell checking asynchronously for DOCX and PPTX"""
    if not update.message.document:
        await update.message.reply_text(
            "Iltimos, Word (.docx) yoki PowerPoint (.pptx) fayl yuboring.",
            reply_markup=get_back_button()
        )
        return
    
    file_name = update.message.document.file_name or "file.docx"
    ext = os.path.splitext(file_name)[1].lower()
    
    if ext not in SUPPORTED_EXTS:
        await update.message.reply_text(
            "❌ Faqat .DOCX yoki .PPTX fayllar qabul qilinadi.",
            reply_markup=get_back_button()
        )
        return

    status_msg = await update.message.reply_text(
        f"⏳ '{file_name}' tekshirilmoqda...\n"
        "AI imlo xatolarini qidirmoqda (bu biroz vaqt olishi mumkin)..."
    )
    
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.UPLOAD_DOCUMENT
    )
    
    temp_path = None
    output_path = None
    
    try:
        # Download file
        file = await update.message.document.get_file()
        temp_path = f"temp_spell_{update.effective_user.id}_{int(time.time())}{ext}"
        await file.download_to_drive(temp_path)
        
        # Choose correct spell checker
        if ext == '.pptx':
            output_path, errors, fixed = await check_spelling_pptx(temp_path)
        else:
            output_path, errors, fixed = await check_spelling_gemini(temp_path)
        
        if not output_path or not os.path.exists(output_path):
            raise Exception("Tuzatilgan fayl saqlanmadi")
        
        # Send result
        out_name = f"Tuzatilgan_{file_name}"
        with open(output_path, "rb") as f:
            await update.message.reply_document(
                document=InputFile(f, filename=out_name),
                caption=(
                    f"✅ Imlo tekshirish yakunlandi!\n\n"
                    f"📊 Natijalar:\n"
                    f"• Tuzatilgan: {fixed} ta o'zgarish"
                ),
                reply_markup=get_back_button()
            )
        
        await status_msg.delete()
        
    except Exception as e:
        logger.error(f"Spell check handler error: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ Xatolik yuz berdi: {e}")
    
    finally:
        # Cleanup
        for p in [temp_path, output_path]:
            if p and os.path.exists(p):
                try: os.remove(p)
                except: pass
        
        context.user_data.pop('waiting_for', None)
