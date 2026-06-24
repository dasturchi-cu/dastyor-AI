"""Telegram BotFather slash commands (synced on startup)."""
from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeDefault,
)

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
    """
    Faqat shaxsiy chatda toza /start, /cv, ...
    Guruhlarda Telegram /start@Bot ko'rinishini olib tashlash uchun buyruqlar o'chiriladi.
    """
    try:
        private_scope = BotCommandScopeAllPrivateChats()
        await bot.set_my_commands(list(BOT_COMMANDS), scope=private_scope)
        # Eski global/guruh scope — /cmd@DastyorAiBot menyusini tozalaydi
        for scope in (BotCommandScopeDefault(), BotCommandScopeAllGroupChats()):
            try:
                await bot.delete_my_commands(scope=scope)
            except Exception as exc:
                logger.debug("delete_my_commands scope=%s: %s", scope.__class__.__name__, exc)
        logger.info("Bot commands registered (%d, private chats only)", len(BOT_COMMANDS))
    except Exception as exc:
        logger.warning("set_my_commands failed: %s", exc)
