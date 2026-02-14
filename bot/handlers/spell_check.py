"""
Imlo Tekshirish (Spell Check) Handler
Uses ai_service to check spelling asynchronously.
"""
import os
import time
import logging
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from bot.keyboards.reply_keyboards import get_back_button
from bot.services.ai_service import check_spelling_gemini

logger = logging.getLogger(__name__)


async def spell_check_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle spell check request"""
    await update.message.reply_text(
        "✅ **Imlo Tekshirish**\n\n"
        "Word (.docx) hujjat yuboring.\n"
        "AI imlo xatolarini aniqlaydi va tuzatilgan faylni qaytaradi.\n\n"
        "💡 Hozircha o'zbek va rus tillarini qo'llab-quvvatlaydi.",
        reply_markup=get_back_button(),
        parse_mode="Markdown"
    )
    context.user_data['waiting_for'] = 'spell_check_doc'


async def process_spell_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process spell checking asynchronously"""
    if not update.message.document:
        await update.message.reply_text(
            "Iltimos, Word (.docx) fayl yuboring.",
            reply_markup=get_back_button()
        )
        return
    
    file_name = update.message.document.file_name or "file.docx"
    
    if not file_name.lower().endswith('.docx'):
        await update.message.reply_text(
            "❌ Faqat .DOCX (Word) fayllar qabul qilinadi.",
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
        temp_path = f"temp_spell_{update.effective_user.id}_{int(time.time())}.docx"
        await file.download_to_drive(temp_path)
        
        # Async Spell Check
        output_path, errors, fixed = await check_spelling_gemini(temp_path)
        
        if not output_path or not os.path.exists(output_path):
            raise Exception("Tuzatilgan fayl saqlanmadi")
        
        # Send result
        with open(output_path, "rb") as f:
            await update.message.reply_document(
                document=InputFile(f, filename=f"Tuzatilgan_{file_name}"),
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
