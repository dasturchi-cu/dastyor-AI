"""Aiogram 3 bot entry point."""
from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import settings
from database.connection import init_db
from features.admin import handlers as admin_handlers
from features.bot.handlers import obyektivka as obyektivka_handlers
from features.bot.handlers import start as start_handlers
from features.bot.handlers import voice as voice_handlers

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def create_bot() -> Bot:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is missing")
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(admin_handlers.router)
    dp.include_router(obyektivka_handlers.router)
    dp.include_router(start_handlers.router)
    dp.include_router(voice_handlers.router)
    return dp


async def run_polling() -> None:
    init_db()
    bot = create_bot()
    dp = create_dispatcher()
    logger.info("Starting Aiogram 3 polling...")
    await dp.start_polling(bot, drop_pending_updates=True)


def main() -> None:
    if not settings.bot_token:
        logger.critical("BOT_TOKEN missing — set in .env")
        sys.exit(1)
    asyncio.run(run_polling())


if __name__ == "__main__":
    main()
