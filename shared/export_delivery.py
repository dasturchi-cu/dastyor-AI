"""Send generated documents to the user's Telegram chat."""
from __future__ import annotations

import logging
from io import BytesIO

from telegram import InputFile

logger = logging.getLogger(__name__)


async def send_bytes_to_telegram(
    bot,
    chat_id: int,
    data: bytes,
    filename: str,
    *,
    caption: str | None = None,
) -> bool:
    if not bot or not chat_id or not data:
        return False
    try:
        await bot.send_document(
            chat_id=int(chat_id),
            document=InputFile(BytesIO(data), filename=filename),
            caption=caption,
        )
        return True
    except Exception as e:
        logger.exception("Telegram delivery failed chat_id=%s file=%s: %s", chat_id, filename, e)
        return False
