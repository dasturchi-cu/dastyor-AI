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
    BotCommand(command="cover", description="AI Muqova xati (Cover Letter) yozish"),
    BotCommand(command="translate", description="Hujjatni boshqa tilga tarjima qilish"),
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

        # Synchronize Telegram Bot Chat Menu Button (bottom-left app button in Telegram)
        from config.settings import settings
        from aiogram.types import MenuButtonWebApp, WebAppInfo

        base_url = (settings.webapp_base or "").strip().rstrip("/")
        if base_url.startswith("https://"):
            webapp_main_url = f"{base_url}/index.html"
            try:
                await bot.set_chat_menu_button(
                    menu_button=MenuButtonWebApp(
                        text="🚀 Web App",
                        web_app=WebAppInfo(url=webapp_main_url),
                    )
                )
                logger.info("Bot menu button set to WebApp: %s", webapp_main_url)
            except Exception as mb_err:
                logger.warning("Failed to set chat menu button: %s", mb_err)
    except Exception as exc:
        logger.warning("set_my_commands failed: %s", exc)
