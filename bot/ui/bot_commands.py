"""Telegram «/» buyruqlar ro‘yxati — deployda avtomatik yangilanadi."""
from __future__ import annotations

import logging

from telegram import Bot, BotCommand

logger = logging.getLogger(__name__)

# Faqat minimal botda ishlaydigan buyruqlar (main.py handlerlari bilan mos)
DEFAULT_BOT_COMMANDS: tuple[BotCommand, ...] = (
    BotCommand("start", "Bosh menyu — CV va Obyektivka"),
    BotCommand("docs", "Mening hujjatlarim — to‘lov holati"),
    BotCommand("help", "Yordam"),
    BotCommand("contact", "Murojaat (admin bilan bog‘lanish)"),
)


async def sync_bot_commands(bot: Bot) -> None:
    """Eski /ocr, /pdf, /premium va hokazolarni olib tashlab ro‘yxatni almashtiradi."""
    try:
        await bot.set_my_commands(list(DEFAULT_BOT_COMMANDS))
        logger.info("Telegram /commands synced: %s", [c.command for c in DEFAULT_BOT_COMMANDS])
    except Exception as e:
        logger.warning("set_my_commands failed: %s", e)
