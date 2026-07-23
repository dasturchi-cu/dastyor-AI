"""Send generated documents to the user's Telegram chat (aiogram)."""
from __future__ import annotations

import logging
from typing import Any

from aiogram.types import BufferedInputFile

logger = logging.getLogger(__name__)


async def send_bytes_to_telegram(
    bot,
    chat_id: int,
    data: bytes,
    filename: str,
    *,
    caption: str | None = None,
    reply_markup: Any | None = None,
    with_referral_share: bool = False,
) -> bool:
    if not bot or not chat_id or not data:
        return False
    markup = reply_markup
    text = caption
    if with_referral_share:
        from shared.keyboards import document_ready_share_note, referral_share_keyboard

        if markup is None:
            markup = referral_share_keyboard(int(chat_id))
        if text:
            text = f"{text}{document_ready_share_note()}"
        else:
            text = document_ready_share_note().lstrip()
    try:
        use_html = bool(with_referral_share) or (bool(text) and "<" in text)
        await bot.send_document(
            chat_id=int(chat_id),
            document=BufferedInputFile(data, filename=filename),
            caption=text,
            reply_markup=markup,
            parse_mode="HTML" if use_html else None,
        )
        return True
    except Exception as e:
        logger.exception("Telegram delivery failed chat_id=%s file=%s: %s", chat_id, filename, e)
        return False
