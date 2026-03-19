import logging
import os
from typing import Any

from telegram import InputFile

logger = logging.getLogger(__name__)


async def send_docx_with_confirmation(
    bot,
    chat_id: int,
    document: Any,
    *,
    filename: str,
    caption: str | None = None,
    parse_mode: str | None = None,
    reply_markup=None,
    send_confirmation: bool = False,
) -> bool:
    """
    Send a DOCX file and then send a confirmation message only on success.
    If sending fails, attempts to send an explicit failure message.
    """
    try:
        # BytesIO / file-like pointer safety.
        try:
            if hasattr(document, "seek"):
                document.seek(0)
        except Exception:
            pass

        # If it's BytesIO, Telegram upload sometimes behaves better with raw bytes.
        file_for_upload = document
        try:
            if hasattr(document, "getvalue"):
                file_for_upload = document.getvalue()
        except Exception:
            pass

        await bot.send_document(
            chat_id=chat_id,
            document=InputFile(file_for_upload, filename=filename),
            caption=caption,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
        if send_confirmation:
            await bot.send_message(chat_id=chat_id, text="✅ Word fayl yuborildi.")
        return True
    except Exception as e:
        logger.error(
            "send_docx_with_confirmation failed chat_id=%s filename=%s err=%s",
            chat_id,
            filename,
            e,
            exc_info=True,
        )
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ Word fayl yuborishda xatolik yuz berdi: {str(e)[:200]}",
            )
        except Exception:
            pass
        return False


async def send_file_safely(
    bot,
    chat_id: int,
    file_path: str,
    *,
    caption: str | None = None,
    parse_mode: str | None = None,
    confirmation_text: str | None = None,
) -> bool:
    """
    Robust file delivery helper:
    - Ensures file exists before sending
    - Uses send_document with an opened file handle
    - Sends confirmation only after successful upload
    """
    try:
        if not file_path or not os.path.isfile(file_path):
            await bot.send_message(chat_id=chat_id, text="❌ Fayl yaratilmadi")
            return False

        filename = os.path.basename(file_path) or "document"
        try:
            size = os.path.getsize(file_path)
        except Exception:
            size = -1
        logger.info("Sending file: %s (size=%s) to chat_id=%s", file_path, size, chat_id)
        with open(file_path, "rb") as f:
            await bot.send_document(
                chat_id=chat_id,
                document=f,
                caption=caption,
                parse_mode=parse_mode,
            )

        if confirmation_text:
            await bot.send_message(chat_id=chat_id, text=confirmation_text)
        return True
    except Exception as e:
        logger.error("File send failed path=%s chat_id=%s err=%s", file_path, chat_id, e, exc_info=True)
        try:
            await bot.send_message(chat_id=chat_id, text=f"❌ Fayl yuborilmadi: {str(e)[:200]}")
        except Exception:
            pass
        return False
