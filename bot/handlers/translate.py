import os
import time
import logging
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from bot.keyboards.reply_keyboards import get_translate_menu, get_back_button
from bot.services.ai_service import (
    is_meaningfully_changed,
    translate_document_gemini,
    translate_pptx,
    translate_text,
)
from bot.services.document_text_extract import extract_plain_text_from_bytes
from bot.services.plan_limits import CAT_TRANSLATE
from bot.services.user_service import get_user_lang, record_service_completion
from bot.services.usage_tracker import reply_if_daily_quota_blocked
from bot.constants.states import WaitingState

logger = logging.getLogger(__name__)

DIRECTION_MAP = {
    'uz_en': "O'zbek → Ingliz",
    'en_uz': "Ingliz → O'zbek",
    'ru_uz': "Rus → O'zbek",
    'uz_ru': "O'zbek → Rus",
    'ru_en': "Rus → Ingliz",
}

TARGET_LANG = {
    'uz_en': 'en',
    'en_uz': 'uz',
    'ru_uz': 'uz',
    'uz_ru': 'ru',
    'ru_en': 'en',
}

SUPPORTED_EXTENSIONS = ('.docx', '.txt', '.pptx', '.pdf', '.xlsx')


async def translate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show translation direction menu"""
    await update.message.reply_text(
        "🌐 <b>Hujjat / Matn Tarjimasi</b>\n\n"
        "Til yo'nalishini tanlang:",
        reply_markup=get_translate_menu(),
        parse_mode="HTML"
    )


async def set_translation_direction(update: Update, context: ContextTypes.DEFAULT_TYPE, direction: str):
    """Store direction and prompt user to send text or file"""
    context.user_data['translate_direction'] = direction
    context.user_data['waiting_for'] = WaitingState.TRANSLATE_INPUT

    label = DIRECTION_MAP.get(direction, "Tarjima")
    await update.message.reply_text(
        f"🔄 <b>{label}</b>\n\n"
        "📝 Matn yoki 📄 DOCX/PPTX/PDF/TXT/XLSX fayl yuboring.\n"
        "<i>Matn yuborsangiz — natija chatga chiqariladi.\n"
        "Fayl yuborsangiz — tarjima qilingan fayl yuboriladi.</i>",
        reply_markup=get_back_button(),
        parse_mode="HTML"
    )


async def process_translation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Main entry point for translation.
    Handles both plain text and DOCX file messages.
    Called from handle_router_text (plain text) and handle_router_doc (file).
    """
    try:
        direction = context.user_data.get('translate_direction')
        if not direction:
            await translate_handler(update, context)
            return

        message = update.message
        text_input = (context.user_data.pop("_normalized_text_input", None) or "").strip()

        if message.text or text_input:
            text_in = (message.text or text_input).strip()
            if len(text_in) < 2:
                await message.reply_text("❌ Matn juda qisqa.")
                return

            uid = message.from_user.id
            if await reply_if_daily_quota_blocked(update, uid, category=CAT_TRANSLATE, lang=get_user_lang(uid)):
                return

            label = DIRECTION_MAP.get(direction, direction)
            status_msg = await message.reply_text(f"⏳ {label} tarjima qilinmoqda...")
            await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
            try:
                import html as html_mod
                result = await translate_text(text_in, direction)
                if not is_meaningfully_changed(text_in, result):
                    raise Exception("Tarjima natijasi original bilan bir xil chiqdi")
                await status_msg.delete()
                await message.reply_text(html_mod.escape(result), reply_markup=get_back_button())
                record_service_completion(uid, CAT_TRANSLATE, "Translate Text")
            except Exception as e:
                logger.error(f"Text translation error: {e}", exc_info=True)
                await status_msg.edit_text("❌ Tarjimada xatolik yuz berdi.")
            return

        if message.document:
            doc = message.document
            file_name = doc.file_name or "document.docx"
            ext = os.path.splitext(file_name)[1].lower()

            if ext not in SUPPORTED_EXTENSIONS:
                await message.reply_text(
                    f"❌ <b>{ext}</b> formati qo'llab-quvvatlanmaydi.\n"
                    "Faqat <b>.docx, .txt, .pptx, .pdf, .xlsx</b> fayllar qabul qilinadi.",
                    parse_mode="HTML",
                )
                return

            uid = message.from_user.id
            if await reply_if_daily_quota_blocked(update, uid, category=CAT_TRANSLATE, lang=get_user_lang(uid)):
                return

            label = DIRECTION_MAP.get(direction, direction)
            target_lang = TARGET_LANG.get(direction, 'uz')
            status_msg = await message.reply_text(
                f"⏳ <b>'{file_name}'</b> tarjima qilinmoqda...\n"
                f"🔄 {label} · AI ishlamoqda, iltimos kuting (30–90 son).",
                parse_mode="HTML",
            )
            await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.UPLOAD_DOCUMENT)

            temp_path = f"temp_translate_{message.from_user.id}_{int(time.time())}{ext}"
            translated_path = None
            try:
                tg_file = await doc.get_file()
                await tg_file.download_to_drive(temp_path)

                if ext == ".docx":
                    translated_path = await translate_document_gemini(temp_path, target_lang)
                    if not translated_path or not os.path.exists(translated_path):
                        with open(temp_path, "rb") as rf:
                            raw = rf.read()
                        src_text = extract_plain_text_from_bytes(file_name, raw)
                        if not (src_text or "").strip():
                            raise Exception("Fayldan matn ajratilmadi")
                        translated_text = await translate_text(src_text, direction)
                        if not translated_text or translated_text.startswith("Tarjimada xato") or translated_text.startswith("AI model"):
                            raise Exception(translated_text or "Tarjima bo'sh qaytdi")
                        if not is_meaningfully_changed(src_text, translated_text):
                            raise Exception("Tarjima natijasi original bilan bir xil chiqdi")
                        translated_path = temp_path.replace(ext, f"_translated_{target_lang}.txt")
                        with open(translated_path, "w", encoding="utf-8") as wf:
                            wf.write(translated_text)
                elif ext == ".pptx":
                    translated_path = await translate_pptx(temp_path, direction, target_lang)
                    if not translated_path or not os.path.exists(translated_path):
                        with open(temp_path, "rb") as rf:
                            raw = rf.read()
                        src_text = extract_plain_text_from_bytes(file_name, raw)
                        if not (src_text or "").strip():
                            raise Exception("Fayldan matn ajratilmadi")
                        translated_text = await translate_text(src_text, direction)
                        if not translated_text or translated_text.startswith("Tarjima vaqtincha mavjud emas."):
                            raise Exception("Tarjima vaqtincha mavjud emas.")
                        if not is_meaningfully_changed(src_text, translated_text):
                            raise Exception("Tarjima natijasi original bilan bir xil chiqdi")
                        translated_path = temp_path.replace(ext, f"_translated_{target_lang}.txt")
                        with open(translated_path, "w", encoding="utf-8") as wf:
                            wf.write(translated_text)
                else:
                    with open(temp_path, "rb") as rf:
                        raw = rf.read()
                    src_text = extract_plain_text_from_bytes(file_name, raw)
                    if not (src_text or "").strip():
                        raise Exception("Fayldan matn ajratilmadi")
                    translated_text = await translate_text(src_text, direction)
                    if not translated_text or translated_text.startswith("Tarjima vaqtincha mavjud emas."):
                        raise Exception("Tarjima vaqtincha mavjud emas.")
                    if not is_meaningfully_changed(src_text, translated_text):
                        raise Exception("Tarjima natijasi original bilan bir xil chiqdi")
                    translated_path = temp_path.replace(ext, f"_translated_{target_lang}.txt")
                    with open(translated_path, "w", encoding="utf-8") as wf:
                        wf.write(translated_text)

                if translated_path and os.path.exists(translated_path):
                    base_name = os.path.splitext(file_name)[0]
                    out_ext = os.path.splitext(translated_path)[1].lower() or ".txt"
                    out_name = f"{base_name}_{target_lang}_@DastyorAiBot{out_ext}"
                    await status_msg.edit_text("✅ Tarjima tayyor! Fayl yuklanmoqda...")
                    with open(translated_path, "rb") as fp:
                        await message.reply_document(
                            document=InputFile(fp, filename=out_name),
                            caption=(
                                f"✅ <b>Tarjima tayyor!</b>\n"
                                f"📄 Original: <code>{file_name}</code>\n"
                                f"🔄 {label}\n"
                                f"📎 <code>{out_name}</code>"
                            ),
                            parse_mode="HTML",
                            reply_markup=get_back_button(),
                        )
                    record_service_completion(message.from_user.id, CAT_TRANSLATE, "Translate Doc")
                else:
                    await status_msg.edit_text(
                        "❌ Tarjima qilishda xatolik yuz berdi.\n"
                        "Fayl formati murakkab yoki bo'sh bo'lishi mumkin."
                    )
            except Exception as e:
                logger.error(f"Document translation error: {e}", exc_info=True)
                await status_msg.edit_text("❌ Tarjima vaqtincha bajarilmadi. Iltimos keyinroq qayta urinib ko'ring.")
            finally:
                for p in [temp_path, translated_path]:
                    if p and os.path.exists(p):
                        try:
                            os.remove(p)
                        except Exception:
                            pass
                context.user_data.pop('translate_direction', None)
                context.user_data.pop('waiting_for', None)
            return

        await message.reply_text("📝 Matn yoki 📄 DOCX fayl yuboring.", reply_markup=get_back_button())
    except Exception as e:
        logger.error("process_translation error: %s", e, exc_info=True)
        try:
            await update.message.reply_text("⚠️ Xatolik yuz berdi. Iltimos qayta urinib ko'ring.")
        except Exception:
            pass
