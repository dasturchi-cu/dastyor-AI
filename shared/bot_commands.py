"""Telegram BotFather slash commands (synced on startup)."""
from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import BotCommand

logger = logging.getLogger(__name__)

BOT_COMMANDS: tuple[BotCommand, ...] = (
    BotCommand(command="start", description="Bosh menyu"),
    BotCommand(command="cv", description="CV resume yaratish"),
    BotCommand(command="obyektivka", description="Obyektivka yaratish"),
    BotCommand(command="balance", description="To'lov va kirish holati"),
    BotCommand(command="contact", description="Bog'lanish"),
    BotCommand(command="help", description="Yordam"),
)


async def register_bot_commands(bot: Bot) -> None:
    try:
        await bot.set_my_commands(list(BOT_COMMANDS))
        logger.info("Bot commands registered (%d)", len(BOT_COMMANDS))
    except Exception as exc:
        logger.warning("set_my_commands failed: %s", exc)
