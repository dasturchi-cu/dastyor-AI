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
