"""Send generated documents to the user's Telegram chat (aiogram)."""
from __future__ import annotations

import logging

from aiogram.types import BufferedInputFile

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
            document=BufferedInputFile(data, filename=filename),
            caption=caption,
        )
        return True
    except Exception as e:
        logger.exception("Telegram delivery failed chat_id=%s file=%s: %s", chat_id, filename, e)
        return False
