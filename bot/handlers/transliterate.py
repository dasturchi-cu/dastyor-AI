"""
Kirill ↔ Lotin Transliteration Handler
Supports both text messages and DOCX files.
"""
import os
import time
import logging
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from bot.keyboards.reply_keyboards import get_krill_lotin_menu, get_back_button, get_main_menu
from bot.services.transliterate_service import transliterate
from bot.utils.helpers import is_back_button

logger = logging.getLogger(__name__)


async def transliterate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Cyrillic-Latin conversion menu"""
    await update.message.reply_text(
        "✏️ **Kirill ↔ Lotin**\n\n"
        "Yo'nalishni tanlang:",
        reply_markup=get_krill_lotin_menu(),
        parse_mode="Markdown"
    )


async def krill_to_lotin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Cyrillic to Latin conversion"""
    await update.message.reply_text(
        "📝 **Kirill → Lotin**\n\n"
        "Matn yoki hujjat (DOCX) yuboring.\n"
        "Matn yuborsangiz — darhol aylantirib beraman.\n"
        "DOCX yuborsangiz — fayl ichidagi barcha matn o'zgartiriladi.",
        reply_markup=get_back_button()
    )
    context.user_data['transliterate_direction'] = 'krill_to_lotin'


async def lotin_to_krill_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Latin to Cyrillic conversion"""
    await update.message.reply_text(
        "📝 **Lotin → Kirill**\n\n"
        "Matn yoki hujjat (DOCX) yuboring.\n"
        "Matn yuborsangiz — darhol aylantirib beraman.\n"
        "DOCX yuborsangiz — fayl ichidagi barcha matn o'zgartiriladi.",
        reply_markup=get_back_button()
    )
    context.user_data['transliterate_direction'] = 'lotin_to_krill'


async def process_transliteration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process transliteration request (text or DOCX)"""
    direction = context.user_data.get('transliterate_direction')

    if not direction:
        return

    # TEXT MESSAGE
    if update.message.text:
        text = update.message.text
        
        if is_back_button(text):
            context.user_data.pop('transliterate_direction', None)
            await update.message.reply_text(
                "🏠 Asosiy menyu",
                reply_markup=get_main_menu(update.effective_user.id if update.effective_user else None)
            )
            return
        
        result_text = transliterate(text, direction)
        await update.message.reply_text(
            f"✅ Natija:\n\n{result_text}",
            reply_markup=get_back_button()
        )
        # Don't clear direction so user can send more text
        return

    # DOCX FILE
    if update.message.document:
        file_name = update.message.document.file_name or "file.docx"
        
        if not file_name.lower().endswith('.docx'):
            await update.message.reply_text(
                "❌ Faqat .DOCX (Word) fayllar qabul qilinadi.",
                reply_markup=get_back_button()
            )
            return

        status_msg = await update.message.reply_text(
            f"⏳ '{file_name}' transliteratsiya qilinmoqda..."
        )
        
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, 
            action=ChatAction.UPLOAD_DOCUMENT
        )

        temp_path = None
        output_path = None
        
        try:
            from docx import Document
            
            # Download
            file = await update.message.document.get_file()
            temp_path = f"temp_translit_{update.effective_user.id}_{int(time.time())}.docx"
            await file.download_to_drive(temp_path)
            
            # Open and transliterate
            doc = Document(temp_path)
            
            # Process paragraphs
            for para in doc.paragraphs:
                if para.text.strip():
                    for run in para.runs:
                        if run.text.strip():
                            run.text = transliterate(run.text, direction)
            
            # Process tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for para in cell.paragraphs:
                            for run in para.runs:
                                if run.text.strip():
                                    run.text = transliterate(run.text, direction)
            
            # Save
            dir_label = "lotin" if direction == "krill_to_lotin" else "krill"
            output_path = f"Translit_{dir_label}_{file_name}"
            doc.save(output_path)
            
            # Send
            with open(output_path, "rb") as f:
                await update.message.reply_document(
                    document=InputFile(f, filename=output_path),
                    caption=f"✅ Transliteratsiya tayyor!\n\nYo'nalish: {dir_label.upper()}",
                    reply_markup=get_back_button()
                )
            
            await status_msg.delete()
            
        except Exception as e:
            logger.error(f"Transliteration DOCX error: {e}", exc_info=True)
            await status_msg.edit_text(f"❌ Xatolik: {e}")
        
        finally:
            for p in [temp_path, output_path]:
                if p and os.path.exists(p):
                    try: os.remove(p)
                    except: pass
        
        context.user_data.pop('transliterate_direction', None)
