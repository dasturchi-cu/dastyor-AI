"""
OCR to Word AI Handler (HTML Table Support)
"""
import os
import time
import logging
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from docx import Document
from bs4 import BeautifulSoup
from bot.keyboards.reply_keyboards import get_back_button, get_main_menu
from bot.utils.helpers import is_back_button
from bot.services.ocr_service import extract_text_from_image
from bot.utils.progress import send_progress, update_progress

logger = logging.getLogger(__name__)

async def ocr_to_word_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start OCR process explanation"""
    user_id = update.message.from_user.id
    
    # Check if back button pressed
    if is_back_button(update.message.text):
        if 'waiting_for' in context.user_data:
            del context.user_data['waiting_for']
            
        await update.message.reply_text(
            "🏠 **Asosiy menyuga qaytildi**",
            reply_markup=get_main_menu(),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    instruction_text = (
        "📸 **Rasm → Word AI**\n\n"
        "Bu xizmat orqali rasm ichidagi matnni Word hujjatiga o'tkazish mumkin.\n\n"
        "✨ **Afzalliklar:**\n"
        "• Shrift saqlanadi\n"
        "• Jadvallar tuzilishi saqlanadi (HTML based)\n"
        "• Ustun va satrlar to'g'ri joylashadi\n\n"
        "📤 **Davom etish:**\n"
        "Menga rasm yuboring (JPG, PNG). Hozircha bitta rasm qabul qilaman."
    )
    
    await update.message.reply_text(
        instruction_text,
        reply_markup=get_back_button(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    context.user_data['waiting_for'] = 'ocr_image'


from docx.shared import Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

def add_html_to_docx(doc, html_content):
    """Parses HTML and maps it to Word layout (tables, widths, alignment)"""
    
    # Set Narrow Margins (1.27 cm) for better 1:1 fit
    section = doc.sections[0]
    section.left_margin = Cm(1.27)
    section.right_margin = Cm(1.27)
    section.top_margin = Cm(1.27)
    section.bottom_margin = Cm(1.27)
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for element in soup.children:
        if element.name == None: continue 
        
        if element.name == 'table':
            rows = element.find_all('tr')
            if not rows: continue
            
            # Count cols
            max_cols = 0
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) > max_cols: max_cols = len(cols)
            
            if max_cols > 0:
                table = doc.add_table(rows=len(rows), cols=max_cols)
                table.style = 'Table Grid'
                table.autofit = False # Disable autofit to use manual widths
                table.allow_autofit = False
                
                # Check for widths in the first row
                total_width = section.page_width - section.left_margin - section.right_margin
                first_row_cols = rows[0].find_all(['td', 'th'])
                
                # Try to apply widths if provided
                try:
                    for j, col in enumerate(first_row_cols):
                        width_attr = col.get('width', '').replace('%', '')
                        if width_attr and width_attr.isdigit() and j < max_cols:
                            percent = int(width_attr)
                            width_val = total_width * (percent / 100)
                            # Apply to all cells in this column
                            for r_idx in range(len(rows)):
                                try:
                                    table.cell(r_idx, j).width = width_val
                                except: pass
                except Exception as w_err:
                     logger.warning(f"Width error: {w_err}")

                for i, row in enumerate(rows):
                    cols = row.find_all(['td', 'th'])
                    for j, col in enumerate(cols):
                        if j < max_cols:
                            cell = table.cell(i, j)
                            # Clear default paragraph
                            cell._element.clear_content()
                            p = cell.add_paragraph()
                            
                            text = col.get_text(strip=True)
                            if not text: continue
                            
                            run = p.add_run(text)
                            
                            if col.find('b') or col.name == 'th':
                                run.bold = True
                            
                            align = col.get('align', '').lower()
                            if align == 'center':
                                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            elif align == 'right':
                                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

        elif element.name in ['p', 'div', 'h1', 'h2', 'h3', 'h4']:
            p = doc.add_paragraph()
            text = element.get_text(strip=True)
            if not text: continue
            
            run = p.add_run(text)
            
            # Handle Headers
            if element.name == 'h1':
                p.style = 'Heading 1'
            elif element.name == 'h2':
                p.style = 'Heading 2'
            elif element.name == 'h3':
                p.style = 'Heading 3'
            
            # Handle Bold
            if element.name == 'b' or element.find('b'):
                run.bold = True
                
            # Handle Alignment
            align = element.get('align', '').lower()
            if align == 'center':
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            elif align == 'right':
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                
        elif element.name == 'ul':
            for li in element.find_all('li'):
                doc.add_paragraph(li.get_text(strip=True), style='List Bullet')
                
        elif element.name == 'ol':
            for li in element.find_all('li'):
                doc.add_paragraph(li.get_text(strip=True), style='List Number')


async def handle_ocr_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the uploaded image for OCR"""
    message = update.message
    
    # Check if back button
    if message.text and is_back_button(message.text):
        del context.user_data['waiting_for']
        await update.message.reply_text(
            "🏠 **Asosiy menyuga qaytildi**",
            reply_markup=get_main_menu(),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Check if photo received
    if not message.photo and not message.document:
        await update.message.reply_text(
            "⚠️ Iltimos, rasm yuboring (JPG yoki PNG formatda).",
            reply_markup=get_back_button()
        )
        return

    # Initial Progress
    progress_msg = await send_progress(context, update.effective_chat.id, "Rasm qabul qilindi...")
    
    # Send typing action
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)

    temp_image_path = None
    doc_path = None
    
    try:
        await update_progress(context, progress_msg, 10, "Fayl yuklanmoqda...")
        
        # Get file object
        if message.document:
             file_obj = await message.document.get_file()
             file_name = message.document.file_name or "image.jpg"
        else:
             file_obj = await message.photo[-1].get_file()
             file_name = f"image_{message.id}.jpg"

        # Download file
        temp_image_path = f"temp_ocr_{update.effective_user.id}_{int(time.time())}.jpg"
        await file_obj.download_to_drive(temp_image_path)
        
        await update_progress(context, progress_msg, 40, "AI matnni o'qimoqda...")
        
        # Extract Text (HTML format)
        extracted_text = await extract_text_from_image(temp_image_path)
        
        if not extracted_text:
            await progress_msg.edit_text("❌ **Xatolik:** Matn ajratilmadi.")
            return
            
        await update_progress(context, progress_msg, 70, "Word hujjat shakllantirilmoqda...")
        
        # Create Word Document
        doc = Document()
        doc.add_heading('OCR Natijasi', 0)
        
        # Parse HTML to Docx
        try:
            add_html_to_docx(doc, extracted_text)
        except Exception as parse_err:
            logger.error(f"HTML Parse error: {parse_err}")
            doc.add_paragraph(extracted_text)
        
        await update_progress(context, progress_msg, 90, "Fayl yuborilmoqda...")
        
        doc_path = f"Ocr_Natija_{update.effective_user.id}.docx"
        doc.save(doc_path)
        
        # Send Document
        with open(doc_path, 'rb') as f:
            await update.message.reply_document(
                document=InputFile(f, filename=doc_path),
                caption="✅ **Marhamat!**\n\nSizning hujjatingiz tayyor.",
                reply_markup=get_back_button(),
                parse_mode=ParseMode.MARKDOWN
            )
            
        await progress_msg.delete()
        
    except Exception as e:
        logger.error(f"OCR Error: {e}", exc_info=True)
        await progress_msg.edit_text(f"❌ **Xatolik yuz berdi:** {str(e)}")
        
    finally:
        # Cleanup
        try:
            if temp_image_path and os.path.exists(temp_image_path):
                os.remove(temp_image_path)
            if doc_path and os.path.exists(doc_path):
                os.remove(doc_path)
        except Exception:
            pass
