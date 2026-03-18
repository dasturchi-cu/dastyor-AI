import os
from telegram import InputFile


async def send_docx_with_confirmation(
    bot,
    chat_id: int,
    document,
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
        await bot.send_document(
            chat_id=chat_id,
            document=InputFile(document, filename=filename),
            caption=caption,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
        if send_confirmation:
            await bot.send_message(chat_id=chat_id, text="✅ Word fayl yuborildi.")
        return True
    except Exception:
        try:
            await bot.send_message(chat_id=chat_id, text="❌ Word fayl yuborishda xatolik yuz berdi.")
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
        if not file_path or not os.path.exists(file_path):
            await bot.send_message(chat_id=chat_id, text="❌ Fayl yaratilmadi")
            return False

        filename = os.path.basename(file_path) or "document"
        with open(file_path, "rb") as f:
            await bot.send_document(
                chat_id=chat_id,
                document=InputFile(f, filename=filename),
                caption=caption,
                parse_mode=parse_mode,
            )

        if confirmation_text:
            await bot.send_message(chat_id=chat_id, text=confirmation_text)
        return True
    except Exception:
        try:
            await bot.send_message(chat_id=chat_id, text="❌ Fayl yuborishda xatolik yuz berdi")
        except Exception:
            pass
        return False
