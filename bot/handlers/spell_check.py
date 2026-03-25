"""
Imlo Tekshirish (Spell Check) Handler
Uses ai_service to check spelling asynchronously.
Supports plain text, .txt, .docx, .pptx and .pdf inputs.
"""
import os
import time
import logging
import tempfile
import shutil
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from bot.keyboards.reply_keyboards import get_back_button
from bot.services.ai_service import check_spelling_gemini, check_spelling_pptx, check_spelling_text
from bot.services.document_text_extract import extract_plain_text_from_bytes
from bot.services.plan_limits import CAT_SPELL
from bot.services.user_service import get_user_lang, record_service_completion
from bot.services.usage_tracker import reply_if_daily_quota_blocked

logger = logging.getLogger(__name__)

SUPPORTED_EXTS = ('.txt', '.docx', '.pptx', '.pdf')


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
        "Oddiy matn, .txt, Word (.docx), PowerPoint (.pptx) yoki PDF yuboring.\n"
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
            uid = update.effective_user.id
            if await reply_if_daily_quota_blocked(
                update, uid, category=CAT_SPELL, lang=get_user_lang(uid)
            ):
                return
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
            record_service_completion(uid, CAT_SPELL, "Spell Check Text")
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
            "❌ Faqat .TXT, .DOCX, .PPTX yoki .PDF fayllar qabul qilinadi.",
            reply_markup=get_back_button()
        )
        return

    uid = update.effective_user.id
    if await reply_if_daily_quota_blocked(
        update, uid, category=CAT_SPELL, lang=get_user_lang(uid)
    ):
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
    file_sent = False
    
    try:
        # Download file
        file = await update.message.document.get_file()
        temp_path = f"temp_spell_{update.effective_user.id}_{int(time.time())}{ext}"
        await file.download_to_drive(temp_path)
        
        async def _plain_fallback_from_file(path: str, name_hint: str) -> tuple[str, int, int]:
            with open(path, "rb") as rf:
                raw = rf.read()
            source_text = extract_plain_text_from_bytes(name_hint, raw)
            if not (source_text or "").strip():
                raise Exception("Fayldan matn ajratilmadi")
            corrected_text, fixed_local = await check_spelling_text(source_text)
            out_path = path.replace(ext, "_checked.txt")
            with open(out_path, "w", encoding="utf-8") as wf:
                wf.write(corrected_text)
            return out_path, int(fixed_local or 0), int(fixed_local or 0)

        # Choose correct spell checker
        if ext == '.pptx':
            try:
                output_path, errors, fixed = await check_spelling_pptx(temp_path)
            except Exception:
                output_path, errors, fixed = await _plain_fallback_from_file(temp_path, file_name)
        elif ext == '.docx':
            try:
                output_path, errors, fixed = await check_spelling_gemini(temp_path)
            except Exception:
                output_path, errors, fixed = await _plain_fallback_from_file(temp_path, file_name)
        else:
            if ext == ".txt":
                source_text = _read_text_file(temp_path)
            else:
                with open(temp_path, "rb") as rf:
                    raw = rf.read()
                source_text = extract_plain_text_from_bytes(file_name, raw)
            if not (source_text or "").strip():
                raise Exception("Fayldan matn ajratilmadi")
            corrected_text, fixed = await check_spelling_text(source_text)
            output_path = temp_path.replace(ext, "_checked.txt")
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
        file_sent = True
        await status_msg.delete()
        await update.message.reply_text("📎 Tuzatilgan fayl yuborildi.", reply_markup=get_back_button())
        record_service_completion(uid, CAT_SPELL, f"Spell Check {ext.upper()}")
        
    except Exception as e:
        logger.error(f"Spell check handler error: {e}", exc_info=True)
        # Guarantee best-effort delivery even if AI/doc conversion fails.
        if not file_sent and temp_path and os.path.exists(temp_path):
            try:
                fallback_path = temp_path.replace(ext, f"_checked{ext}")
                shutil.copyfile(temp_path, fallback_path)
                output_path = fallback_path
                out_name = f"Tuzatilgan_{file_name}"
                with open(output_path, "rb") as f:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=InputFile(f, filename=out_name),
                        caption=(
                            "⚠️ Imlo tekshirishda xatolik yuz berdi, lekin "
                            "fayl qaytarildi (best-effort)."
                        ),
                    )
                await status_msg.delete()
                await update.message.reply_text("📎 Tuzatilgan fayl yuborildi.", reply_markup=get_back_button())
                file_sent = True
                record_service_completion(uid, CAT_SPELL, f"Spell Check {ext.upper()} (fallback)")
            except Exception:
                pass
        if not file_sent:
            await status_msg.edit_text(f"❌ Xatolik yuz berdi: {e}")
    
    finally:
        # Cleanup
        for p in [temp_path, output_path]:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    logger.debug("Cleanup failed (spell_check) path=%s", p, exc_info=True)
        
        context.user_data.pop('waiting_for', None)
