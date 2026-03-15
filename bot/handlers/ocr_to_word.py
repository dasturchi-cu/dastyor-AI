"""
OCR to Word AI Handler (HTML Table Support)
"""
import os
import time
import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from docx import Document
from bs4 import BeautifulSoup
from bot.keyboards.reply_keyboards import get_back_button, get_main_menu
from bot.utils.helpers import is_back_button
from bot.services.user_service import get_user_lang
from bot.services.ocr_service import extract_text_from_image
from bot.utils.progress import send_progress, update_progress
from bot.utils.delivery import send_docx_with_confirmation

from docx.shared import Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

logger = logging.getLogger(__name__)

from bs4.element import NavigableString, Tag

def _add_run_with_style(paragraph_obj, element, bold=False, italic=False, underline=False):
    """Recursively parses HTML elements and adds styled runs to a docx paragraph."""
    is_bold = bold or element.name in ['b', 'strong', 'h1', 'h2', 'h3', 'th']
    is_italic = italic or element.name in ['i', 'em']
    is_underline = underline or element.name in ['u']
    
    for child in element.children:
        if isinstance(child, NavigableString):
            text = str(child).replace('\n', ' ')
            if not text.strip() and text:
                text = ' '
            if text:
                run = paragraph_obj.add_run(text)
                run.bold = is_bold
                run.italic = is_italic
                run.underline = is_underline
        elif isinstance(child, Tag):
            # If we hit block elements inside text contexts, just add a line break
            if child.name in ['br', 'p', 'div'] and child.name != 'br':
                paragraph_obj.add_run().add_break()
                _add_run_with_style(paragraph_obj, child, is_bold, is_italic, is_underline)
            elif child.name == 'br':
                paragraph_obj.add_run().add_break()
            else:
                _add_run_with_style(paragraph_obj, child, is_bold, is_italic, is_underline)

def get_alignment(element):
    """Extract alignment from align attribute or inline style."""
    align_str = element.get('align', '')
    style_str = element.get('style', '')
    if not align_str and style_str:
        style_lower = style_str.lower()
        if 'text-align: center' in style_lower or 'text-align:center' in style_lower: align_str = 'center'
        elif 'text-align: right' in style_lower or 'text-align:right' in style_lower: align_str = 'right'
        elif 'text-align: justify' in style_lower or 'text-align:justify' in style_lower: align_str = 'justify'
    return align_str

def add_html_to_docx(doc, html_content):
    """Parses HTML and maps it to Word layout (tables, widths, alignment, inline fonts, lists)"""
    
    # Set Narrow Margins (1.27 cm) for better 1:1 fit
    if doc.sections:
        section = doc.sections[0]
        section.left_margin = Cm(1.27)
        section.right_margin = Cm(1.27)
        section.top_margin = Cm(1.27)
        section.bottom_margin = Cm(1.27)
    
    soup = BeautifulSoup(html_content, 'html.parser')
    root = soup.body if soup.body else soup
    
    def apply_align(p, align_str):
        if not align_str: return
        align_str = align_str.lower()
        if 'center' in align_str: p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif 'right' in align_str: p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        elif 'justify' in align_str: p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for element in root.children:
        if isinstance(element, NavigableString):
            text = str(element).strip()
            if text:
                doc.add_paragraph(text)
            continue
            
        if element.name == 'table':
            rows = element.find_all('tr', recursive=False)
            if not rows and element.tbody:
                rows = element.tbody.find_all('tr', recursive=False)
            if not rows: continue
            
            # Count max cols exactly
            max_cols = 0
            for row in rows:
                cols = row.find_all(['td', 'th'], recursive=False)
                if len(cols) > max_cols: max_cols = len(cols)
            
            if max_cols > 0:
                table = doc.add_table(rows=len(rows), cols=max_cols)
                table.style = 'Table Grid'
                table.autofit = False
                table.allow_autofit = False
                
                total_width = section.page_width - section.left_margin - section.right_margin
                
                # Try to apply widths from first row
                if len(rows) > 0:
                    first_row_cols = rows[0].find_all(['td', 'th'], recursive=False)
                    for j, col in enumerate(first_row_cols):
                        width_attr = col.get('width', '').replace('%', '')
                        if width_attr and width_attr.isdigit() and j < max_cols:
                            percent = int(width_attr)
                            width_val = total_width * (percent / 100)
                            for r_idx in range(len(rows)):
                                try: table.cell(r_idx, j).width = width_val
                                except: pass

                # Fill data
                for i, row in enumerate(rows):
                    cols = row.find_all(['td', 'th'], recursive=False)
                    for j, col in enumerate(cols):
                        if j < max_cols:
                            cell = table.cell(i, j)
                            # Clear default text run
                            p = cell.paragraphs[0]
                            p.text = ""
                            
                            align = get_alignment(col)
                            apply_align(p, align)
                            _add_run_with_style(p, col)
        
        elif element.name in ['p', 'h1', 'h2', 'h3', 'h4', 'div', 'center', 'article', 'section', 'main', 'header', 'footer']:
            style = 'Normal'
            if element.name in ['h1', 'h2', 'h3']:
                style = f"Heading {element.name[-1]}"
            
            p = doc.add_paragraph(style=style)
            align = get_alignment(element)
            if element.name == 'center': align = 'center'
            apply_align(p, align)
            _add_run_with_style(p, element)
            
        elif element.name in ['ul', 'ol']:
            style = 'List Bullet' if element.name == 'ul' else 'List Number'
            for li in element.find_all('li', recursive=False):
                p = doc.add_paragraph(style=style)
                _add_run_with_style(p, li)
                
        elif element.name == 'br':
            doc.add_paragraph()
            
        elif element.name and element.name not in ['html', 'body', 'head', 'style', 'script', 'title', 'meta']:
            # For unrecognized wrappers, process their children directly
            for child in element.children:
                if isinstance(child, NavigableString):
                    text = str(child).strip()
                    if text:
                        doc.add_paragraph(text)
                elif isinstance(child, Tag):
                    style = 'Normal'
                    p = doc.add_paragraph()
                    align = get_alignment(child)
                    apply_align(p, align)
                    _add_run_with_style(p, child)


async def perform_ocr_and_send(context, image_path, chat_id, user_id):
    """
    Reusable function: Takes image path, performs OCR, creates Word doc, and sends it.
    Runs fully async; safe to call from a background task.
    """
    t0 = time.perf_counter()
    logger.info("OCR task started for user_id=%s chat_id=%s", user_id, chat_id)
    progress_msg = await send_progress(context, chat_id, "Jarayon boshlandi...")
    doc_path = None

    try:
        await update_progress(context, progress_msg, 20, "AI matnni o'qimoqda...")
        # Extract Text (HTML format)
        extracted_text = await extract_text_from_image(image_path)
        logger.info("OCR extract done in %.1fs user_id=%s", time.perf_counter() - t0, user_id)
        
        if not extracted_text:
            await progress_msg.edit_text("❌ **Xatolik:** Matn ajratilmadi.")
            return
            
        await update_progress(context, progress_msg, 70, "Word hujjat shakllantirilmoqda...")
        # Create Word Document asynchronously so we don't block the loop
        doc_path = f"Ocr_Natija_{user_id}_{int(time.time())}_@DastyorAiBot.docx"
        
        def create_and_save_doc(html_text, path):
            doc = Document()
            try:
                add_html_to_docx(doc, html_text)
            except Exception as parse_err:
                logger.error(f"HTML Parse error: {parse_err}")
                doc.add_paragraph(str(html_text))
            doc.save(path)

        await asyncio.to_thread(create_and_save_doc, extracted_text, doc_path)
        
        await update_progress(context, progress_msg, 90, "Fayl yuborilmoqda...")
        
        # Send Document
        with open(doc_path, 'rb') as f:
            ok = await send_docx_with_confirmation(
                context.bot,
                chat_id,
                f,
                filename=doc_path,
                caption="✅ **Marhamat!**\n\nSizning hujjatingiz tayyor.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_menu(user_id, get_user_lang(user_id)),
            )
            if not ok:
                return
            
        await progress_msg.delete()
        # CLEAR STATE AFTER SUCCESS (when run from background task, user_data is shared)
        if getattr(context, "user_data", None) and context.user_data.get("waiting_for") == "ocr_image":
            context.user_data.pop("waiting_for", None)
        logger.info("OCR task completed in %.1fs user_id=%s", time.perf_counter() - t0, user_id)
    except Exception as e:
        logger.error("OCR Error user_id=%s: %s", user_id, e, exc_info=True)
        try:
            await progress_msg.edit_text(f"❌ **Xatolik yuz berdi:** {str(e)}")
        except Exception:
            pass
        
    finally:
        # Cleanup
        try:
            if doc_path and os.path.exists(doc_path):
                os.remove(doc_path)
        except Exception: pass


async def ocr_to_word_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start OCR process: collect images then process on 'Tayyor'."""
    context.user_data["waiting_for"] = "ocr_image"
    context.user_data["ocr_images"] = []

    msg = (
        "📜 **Hujjat rasmi → Word AI** ✨\n\n"
        "Rasmlarni yuboring (1–20 ta). Tayyor bo'lgach, *Tayyor* deb yozing yoki tugmani bosing."
    )
    await update.message.reply_text(
        msg,
        reply_markup=get_back_button(),
        parse_mode=ParseMode.MARKDOWN,
    )


def _run_ocr_background(
    bot, chat_id: int, user_id: int, temp_image_path: str, user_data: dict
) -> None:
    """
    Run OCR in a fire-and-forget background task. Does NOT block the event loop.
    Cleans up temp file and updates user_data on completion.
    """
    async def _task():
        try:
            # Build a minimal context-like object for progress/send (no full Update)
            class _Ctx:
                def __init__(self, b, ud):
                    self.bot = b
                    self.user_data = ud
            ctx = _Ctx(bot, user_data)
            await perform_ocr_and_send(ctx, temp_image_path, chat_id, user_id)
        except Exception as e:
            logger.error(f"OCR background task failed: {e}", exc_info=True)
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ **OCR xatolik:** {str(e)}",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                pass
        finally:
            try:
                if temp_image_path and os.path.exists(temp_image_path):
                    os.remove(temp_image_path)
            except Exception:
                pass

    asyncio.create_task(_task())


async def _perform_ocr_batch_and_send(context, bot, chat_id: int, user_id: int, file_ids: list) -> None:
    """
    Download all files, run OCR on each with progress (e.g. "Processing 3/10"),
    merge HTML into one Word doc, send. Runs in background; cleans up temp files.
    """
    t0 = time.perf_counter()
    n = len(file_ids)
    logger.info("OCR batch started user_id=%s chat_id=%s count=%s", user_id, chat_id, n)

    progress_msg = None
    temp_paths = []
    doc_path = None
    try:
        progress_msg = await send_progress(context, chat_id, f"0/{n} — Yuklanmoqda...")
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        for i, fid in enumerate(file_ids):
            try:
                f = await bot.get_file(fid)
                path = os.path.join(temp_dir, f"ocr_batch_{user_id}_{int(time.time())}_{i}.jpg")
                await f.download_to_drive(path)
                temp_paths.append(path)
            except Exception as e:
                logger.warning("Batch download failed for file %s: %s", i, e)
        if not temp_paths:
            await progress_msg.edit_text("❌ Hech qanday rasm yuklanmadi.")
            return

        html_parts = []
        for i, img_path in enumerate(temp_paths):
            pct = 20 + int(70 * (i + 1) / len(temp_paths))
            await update_progress(
                context, progress_msg, pct,
                f"O'qilmoqda {i + 1}/{len(temp_paths)}...",
            )
            text = await extract_text_from_image(img_path)
            if text:
                html_parts.append(f"<div class=\"page-break\">{text}</div>")
            else:
                html_parts.append("<p>[Matn ajratilmadi]</p>")

        await update_progress(context, progress_msg, 90, "Word yaratilmoqda...")
        merged_html = "<body>" + "\n".join(html_parts) + "</body>"
        doc_path = f"Ocr_Natija_{user_id}_{int(time.time())}_@DastyorAiBot.docx"

        def _create_doc():
            doc = Document()
            try:
                add_html_to_docx(doc, merged_html)
            except Exception as parse_err:
                logger.error("Batch HTML parse error: %s", parse_err)
                doc.add_paragraph(merged_html.replace("<br>", "\n").replace("</p>", "\n"))
            doc.save(doc_path)
            return doc_path

        await asyncio.to_thread(_create_doc)

        await update_progress(context, progress_msg, 95, "Yuborilmoqda...")
        with open(doc_path, "rb") as f:
            await send_docx_with_confirmation(
                bot, chat_id, f,
                filename=doc_path,
                caption="✅ **Barcha rasmlar bitta Word faylga birlashtirildi.**",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_menu(user_id, get_user_lang(user_id)),
            )
        await progress_msg.delete()
        if getattr(context, "user_data", None):
            context.user_data.pop("waiting_for", None)
            context.user_data.pop("ocr_images", None)
        logger.info("OCR batch completed in %.1fs user_id=%s count=%s", time.perf_counter() - t0, user_id, n)
    except Exception as e:
        logger.error("OCR batch error user_id=%s: %s", user_id, e, exc_info=True)
        try:
            if progress_msg:
                await progress_msg.edit_text(f"❌ **Xatolik:** {str(e)}")
        except Exception:
            pass
        if getattr(context, "user_data", None):
            context.user_data.pop("waiting_for", None)
            context.user_data.pop("ocr_images", None)
    finally:
        for p in temp_paths:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        if doc_path:
            try:
                if os.path.exists(doc_path):
                    os.remove(doc_path)
            except Exception:
                pass


def _run_ocr_batch_background(bot, chat_id: int, user_id: int, file_ids: list, user_data: dict) -> None:
    """Start batch OCR in background; does not block the event loop."""
    class _Ctx:
        def __init__(self, b, ud):
            self.bot = b
            self.user_data = ud
    ctx = _Ctx(bot, user_data)

    async def _task():
        await _perform_ocr_batch_and_send(ctx, bot, chat_id, user_id, file_ids)

    asyncio.create_task(_task())


async def process_ocr_tayyor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Called when user says 'Tayyor' in OCR mode. Starts batch OCR in background.
    Returns True if batch was started, False otherwise.
    """
    images = context.user_data.get("ocr_images") or []
    if not images:
        return False
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id if update.effective_user else 0
    context.user_data["ocr_images"] = []  # clear so we don't process twice
    _run_ocr_batch_background(context.bot, chat_id, user_id, images, context.user_data)
    await update.message.reply_text(
        f"⏳ {len(images)} ta rasm qayta ishlanmoqda. Natija tez orada yuboriladi.",
        parse_mode=ParseMode.MARKDOWN,
    )
    return True


async def handle_ocr_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle image upload (Direct menu usage). Downloads file then runs OCR in background."""
    message = update.message

    # Check if back button
    if message.text and is_back_button(message.text):
        context.user_data.pop("waiting_for", None)
        context.user_data.pop("ocr_images", None)
        uid = update.effective_user.id if update.effective_user else None
        lang = get_user_lang(uid) if uid else "uz_lat"
        await update.message.reply_text(
            "🏠 **Asosiy menyuga qaytildi**",
            reply_markup=get_main_menu(uid, lang),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if not message.photo and not message.document:
        await update.message.reply_text(
            "⚠️ Iltimos, rasm yuboring (JPG yoki PNG formatda).",
            reply_markup=get_back_button()
        )
        return

    # Collect file_id (no download yet — batch will download on Tayyor)
    if message.document:
        file_id = message.document.file_id
    else:
        file_id = message.photo[-1].file_id

    images = context.user_data.setdefault("ocr_images", [])
    if len(images) >= 20:
        await update.message.reply_text(
            "❌ Maksimum 20 ta rasm. *Tayyor* deb yozing.",
            reply_markup=get_back_button(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    images.append(file_id)
    context.user_data["ocr_images"] = images

    await update.message.reply_text(
        f"✅ {len(images)} ta rasm qabul qilindi.\n\n"
        "Yana rasm yuboring yoki *Tayyor* deb yozing.",
        reply_markup=get_back_button(),
        parse_mode=ParseMode.MARKDOWN,
    )
