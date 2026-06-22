"""Non-blocking Telegram progress message updates."""
from __future__ import annotations

import logging

from aiogram.types import Message

from shared.progress import telegram_message

logger = logging.getLogger(__name__)


async def set_step(status: Message, step: int, *, highlight: str | None = None) -> None:
    try:
        await status.edit_text(telegram_message(step, highlight=highlight))
    except Exception as e:
        logger.debug("Progress edit skipped: %s", e)
