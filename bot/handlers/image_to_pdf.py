import os
import time
import asyncio
import logging
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from bot.keyboards.reply_keyboards import get_main_menu, get_image_to_pdf_keyboard
from bot.services.pdf_service import images_to_pdf
from bot.utils.helpers import is_back_button, sanitize_filename

logger = logging.getLogger(__name__)


async def image_to_pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle image to PDF conversion (start flow)"""
    instruction_text = (
        "📑 **Rasm → PDF**\n\n"
        "Rasmlarni ketma-ket yuboring (2–20 dona).\n"
        "Tayyor bo'lgach, *\"Tayyor\"* deb yozing yoki tugmani bosing.\n\n"
        "Rasmlar ketma-ketlikda bitta PDF faylga birlashtiriladi."
    )

    await update.message.reply_text(
        instruction_text,
        reply_markup=get_image_to_pdf_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

    context.user_data["waiting_for"] = "pdf_images"
    context.user_data["pdf_images"] = []


async def collect_pdf_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collect images for PDF generation and build final PDF when user types 'Tayyor'."""
    message = update.message

    # Orqaga tugmasi
    if message.text and is_back_button(message.text):
        context.user_data.pop("waiting_for", None)
        context.user_data.pop("pdf_images", None)
        await message.reply_text(
            "🏠 **Asosiy menyuga qaytildi**",
            reply_markup=get_main_menu(update.effective_user.id if update.effective_user else None),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Rasm qabul qilish
    if message.photo:
        photo = message.photo[-1]
        pdf_images = context.user_data.get("pdf_images", [])

        if len(pdf_images) >= 20:
            await message.reply_text("❌ Maksimum 20 ta rasm qabul qilinadi.")
            return

        pdf_images.append(photo.file_id)
        context.user_data["pdf_images"] = pdf_images

        await message.reply_text(
            f"✅ Rasm qabul qilindi ({len(pdf_images)} ta).\n\n"
            "Yana rasm yuborishingiz yoki *\"Tayyor\"* deb yozishingiz mumkin.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Tayyor — run PDF build in background so bot stays responsive
    if message.text and ("tayyor" in message.text.lower()):
        images = context.user_data.get("pdf_images", [])

        if not images:
            await message.reply_text("❌ Hech qanday rasm yuklanmagan!")
            return

        if len(images) < 2:
            await message.reply_text("❌ Kamida 2 ta rasm kerak!")
            return

        status_msg = await message.reply_text(
            f"⏳ {len(images)} ta rasm PDF ga aylantirilmoqda. Kutib turing..."
        )
        context.user_data.pop("waiting_for", None)
        context.user_data.pop("pdf_images", None)

        async def _pdf_background():
            temp_dir = "temp"
            os.makedirs(temp_dir, exist_ok=True)
            downloaded_paths = []
            pdf_path = None
            try:
                for idx, file_id in enumerate(images, start=1):
                    try:
                        file = await context.bot.get_file(file_id)
                        img_path = os.path.join(
                            temp_dir,
                            sanitize_filename(
                                f"pdf_{message.from_user.id}_{int(time.time())}_{idx}.jpg"
                            ),
                        )
                        await file.download_to_drive(img_path)
                        downloaded_paths.append(img_path)
                        if len(images) > 2 and idx % 3 == 0:
                            await status_msg.edit_text(
                                f"⏳ Yuklanmoqda {idx}/{len(images)}..."
                            )
                    except Exception as e:
                        logger.warning("PDF download file %s failed: %s", idx, e)
                if not downloaded_paths:
                    await status_msg.edit_text("❌ Hech qanday rasm yuklanmadi.")
                    return

                await status_msg.edit_text(
                    f"⏳ {len(downloaded_paths)} ta rasm PDF ga birlashtirilmoqda..."
                )
                pdf_filename = sanitize_filename(
                    f"Rasmlar_{message.from_user.id}_{int(time.time())}.pdf"
                )
                pdf_path = os.path.join(temp_dir, pdf_filename)
                await asyncio.to_thread(images_to_pdf, downloaded_paths, pdf_path)

                with open(pdf_path, "rb") as f:
                    await context.bot.send_document(
                        chat_id=message.chat_id,
                        document=InputFile(f, filename=pdf_filename),
                        caption="✅ PDF tayyor!\n\nBarcha rasmlar bitta faylga birlashtirildi.",
                        reply_markup=get_image_to_pdf_keyboard(),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                await status_msg.delete()
                logger.info("PDF created for user_id=%s images=%s", message.from_user.id, len(downloaded_paths))
            except Exception as e:
                logger.error("PDF build error: %s", e, exc_info=True)
                await status_msg.edit_text(f"❌ PDF yaratishda xatolik: {e}")
            finally:
                for path in downloaded_paths:
                    try:
                        if os.path.exists(path):
                            os.remove(path)
                    except Exception:
                        pass
                if pdf_path and os.path.exists(pdf_path):
                    try:
                        os.remove(pdf_path)
                    except Exception:
                        pass

        asyncio.create_task(_pdf_background())
        return
