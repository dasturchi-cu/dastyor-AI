import os
import time
import logging
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from bot.keyboards.reply_keyboards import get_translate_menu, get_back_button
from bot.services.ai_service import translate_document_gemini, translate_text

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

SUPPORTED_EXTENSIONS = ('.docx',)  # Extend later: '.pptx', '.xlsx'


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
    context.user_data['waiting_for'] = 'translate_input'

    label = DIRECTION_MAP.get(direction, "Tarjima")
    await update.message.reply_text(
        f"🔄 <b>{label}</b>\n\n"
        "📝 Matn yoki 📄 DOCX fayl yuboring.\n"
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
    direction = context.user_data.get('translate_direction')
    if not direction:
        # User has no active translation session → show menu
        await translate_handler(update, context)
        return

    message = update.message

    # ── Case 1: Plain text ─────────────────────────────────────────────
    if message.text:
        text_in = message.text.strip()
        if len(text_in) < 2:
            await message.reply_text("❌ Matn juda qisqa.")
            return

        label = DIRECTION_MAP.get(direction, direction)
        status_msg = await message.reply_text(f"⏳ {label} tarjima qilinmoqda...")
        await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)

        try:
            import html as html_mod
            result = await translate_text(text_in, direction)
            escaped_result = html_mod.escape(result)
            await status_msg.delete()
            await message.reply_text(
                escaped_result,
                reply_markup=get_back_button()
            )
        except Exception as e:
            logger.error(f"Text translation error: {e}", exc_info=True)
            await status_msg.edit_text("❌ Tarjimada xatolik yuz berdi.")
        return

    # ── Case 2: Document / File ────────────────────────────────────────
    if message.document:
        doc = message.document
        file_name = doc.file_name or "document.docx"
        ext = os.path.splitext(file_name)[1].lower()

        if ext not in SUPPORTED_EXTENSIONS:
            await message.reply_text(
                f"❌ <b>{ext}</b> formati hozircha qo'llab-quvvatlanmaydi.\n"
                "Faqat <b>.docx</b> (Word) fayllar qabul qilinadi.",
                parse_mode="HTML"
            )
            return

        label = DIRECTION_MAP.get(direction, direction)
        target_lang = TARGET_LANG.get(direction, 'uz')

        status_msg = await message.reply_text(
            f"⏳ <b>'{file_name}'</b> tarjima qilinmoqda...\n"
            f"🔄 {label} · AI ishlamoqda, iltimos kuting (30–90 son).",
            parse_mode="HTML"
        )
        await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.UPLOAD_DOCUMENT)

        temp_path = f"temp_translate_{message.from_user.id}_{int(time.time())}{ext}"
        translated_path = None
        try:
            # Download
            tg_file = await doc.get_file()
            await tg_file.download_to_drive(temp_path)

            # Translate
            translated_path = await translate_document_gemini(temp_path, target_lang)

            if translated_path and os.path.exists(translated_path):
                # Build output filename with @DastyorAiBot suffix
                base_name = os.path.splitext(file_name)[0]
                out_name = f"{base_name}_{target_lang}_@DastyorAiBot{ext}"

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
                        reply_markup=get_back_button()
                    )
            else:
                await status_msg.edit_text(
                    "❌ Tarjima qilishda xatolik yuz berdi.\n"
                    "Fayl formati murakkab yoki bo'sh bo'lishi mumkin."
                )

        except Exception as e:
            logger.error(f"Document translation error: {e}", exc_info=True)
            await status_msg.edit_text(f"❌ Kutilmagan xatolik: {str(e)[:100]}")
        finally:
            for p in [temp_path, translated_path]:
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass

        # Clear state after successful file translation
        context.user_data.pop('translate_direction', None)
        context.user_data.pop('waiting_for', None)
        return

    # ── Fallback ───────────────────────────────────────────────────────
    await message.reply_text(
        "📝 Matn yoki 📄 DOCX fayl yuboring.",
        reply_markup=get_back_button()
    )
