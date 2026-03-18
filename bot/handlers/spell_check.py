"""
Imlo Tekshirish (Spell Check) Handler
Uses ai_service to check spelling asynchronously.
Supports plain text, .txt, .docx and .pptx inputs.
"""
import os
import time
import logging
import tempfile
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from bot.keyboards.reply_keyboards import get_back_button
from bot.services.ai_service import check_spelling_gemini, check_spelling_pptx, check_spelling_text

logger = logging.getLogger(__name__)

SUPPORTED_EXTS = ('.txt', '.docx', '.pptx')


def _read_text_file(path: str) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1251", "latin-1"):
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except Exception:
            continue
    raise ValueError("Matnli fayl kodlash formati aniqlanmadi.")


async def spell_check_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle spell check request"""
    await update.message.reply_text(
        " **Imlo Tekshirish**\n\n"
        "Oddiy matn, .txt, Word (.docx) yoki PowerPoint (.pptx) yuboring.\n"
        "AI imlo xatolarini aniqlaydi va tuzatilgan faylni qaytaradi.\n\n"
        "💡 Hozircha o'zbek va rus tillarini qo'llab-quvvatlaydi.",
        reply_markup=get_back_button(),
        parse_mode="Markdown"
    )
    context.user_data['waiting_for'] = 'spell_check_doc'


async def process_spell_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process spell checking for text/.txt/.docx/.pptx and always return a file."""
    # Plain text spell-check support (always return a document)
    if not update.message.document:
        if update.message.text and update.message.text.strip():
            status = await update.message.reply_text("⏳ Matn tekshirilmoqda...")
            corrected, fixes = await check_spelling_text(update.message.text)
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix="_checked.txt",
                prefix=f"spell_{update.effective_user.id}_",
                delete=False,
                encoding="utf-8"
            ) as tf:
                tf.write(corrected)
                output_path = tf.name

            with open(output_path, "rb") as f:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=InputFile(f, filename="Tuzatilgan_matn.txt"),
                    caption=(
                        "✅ Imlo tekshirish yakunlandi!\n\n"
                        f"📊 Tuzatilgan: {fixes} ta o'zgarish"
                    )
                )
            await status.delete()
            try:
                os.remove(output_path)
            except Exception:
                pass
            await update.message.reply_text("📎 Tuzatilgan fayl yuborildi.", reply_markup=get_back_button())
            context.user_data.pop('waiting_for', None)
            return

        await update.message.reply_text(
            "Iltimos, matn yoki .txt / .docx / .pptx fayl yuboring.",
            reply_markup=get_back_button()
        )
        return
    
    file_name = update.message.document.file_name or "file.docx"
    ext = os.path.splitext(file_name)[1].lower()
    
    if ext not in SUPPORTED_EXTS:
        await update.message.reply_text(
            "❌ Faqat .TXT, .DOCX yoki .PPTX fayllar qabul qilinadi.",
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
        elif ext == '.docx':
            output_path, errors, fixed = await check_spelling_gemini(temp_path)
        else:
            source_text = _read_text_file(temp_path)
            corrected_text, fixed = await check_spelling_text(source_text)
            output_path = temp_path.replace(".txt", "_checked.txt")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(corrected_text)
            errors = fixed
        
        if not output_path or not os.path.exists(output_path):
            raise Exception("Tuzatilgan fayl saqlanmadi")
        
        # Send result
        out_name = f"Tuzatilgan_{file_name}"
        with open(output_path, "rb") as f:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=InputFile(f, filename=out_name),
                caption=(
                    f"✅ Imlo tekshirish yakunlandi!\n\n"
                    f"📊 Natijalar:\n"
                    f"• Tuzatilgan: {fixed} ta o'zgarish"
                ),
            )
        await status_msg.delete()
        await update.message.reply_text("📎 Tuzatilgan fayl yuborildi.", reply_markup=get_back_button())
        
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
