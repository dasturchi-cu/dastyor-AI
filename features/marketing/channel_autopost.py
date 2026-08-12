"""Channel Auto-Poster Service — Auto Marketing for Telegram Channel."""
from __future__ import annotations

import asyncio
import logging
import random

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config.settings import Settings

logger = logging.getLogger(__name__)

SHOWCASE_TEMPLATES = [
    {
        "title": "💻 <b>Namunaviy IT Developer CV — 1 daqiqada tayyorlandi!</b>",
        "body": (
            "📌 <b>Kasb:</b> Full-Stack Web Developer\n"
            "🛠 <b>Texnologiyalar:</b> Python, FastAPI, React, PostgreSQL, Docker\n"
            "🌐 <b>Tillar:</b> O'zbekcha (Ona tili), Inglizcha (B2), Ruscha (B1)\n\n"
            "✨ <b>Afzalligi:</b> HR va ATS tizimlaridan 100% muvaffaqiyatli o'tadi!"
        ),
    },
    {
        "title": "✍️ <b>Rasmiy Obyektivka (Ma'lumotnoma) — Davlat standarti!</b>",
        "body": (
            "📌 <b>Hujjat turi:</b> Davlat xizmati va Tashkilotlar uchun Obyektivka\n"
            "📑 <b>Format:</b> Tayyor PDF & DOCX (Word)\n"
            "⏱ <b>Tayyorlanish vaqti:</b> Ovozli xabardan atigi 30 soniyada!\n\n"
            "✨ <b>Afzalligi:</b> QR-kod va avtomatik tartiblangan qarindoshlar jadvali."
        ),
    },
    {
        "title": "⭐️ <b>Foydalanuvchilarimizdan fikrlar!</b>",
        "body": (
            "<i>\"Obyektivkamni vazirlik so'rab qolgandi, shoshilinchda botdan foydalandim. 2 daqiqada tayyor DOCX faylini yuklab oldim. Rahmat!\"</i>\n\n"
            "👥 <b>10,000+</b> dan ortiq foydalanuvchilar @DastyorAiBot xizmatidan mamnun."
        ),
    },
    {
        "title": "📊 <b>Moliya va Bank Sohasidagi Professional CV</b>",
        "body": (
            "📌 <b>Kasb:</b> Bosh Hissobchi / Audit Mutaxassisi\n"
            "💼 <b>Ish tajribasi:</b> 5 yil+ Xalqaro tijorat bankida\n"
            "📈 <b>Natija:</b> 12 ta yangi shablonlar (Finance & Executive) qo'shildi!\n\n"
            "✨ Siz ham o'z sohatingizga mos CV ni hoziroq botda to'ldiring."
        ),
    },
]


def _get_showcase_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    url = f"https://t.me/{bot_username}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Hujjat Yaratish (@DastyorAiBot)", url=url)]
        ]
    )


async def send_channel_autopost(bot: Bot) -> bool:
    """Send an automated marketing showcase post to the configured marketing channel/group."""
    settings = Settings()
    channel_id = settings.marketing_channel_id
    if not channel_id:
        logger.warning("No marketing_channel_id configured for autopost.")
        return False

    item = random.choice(SHOWCASE_TEMPLATES)
    caption = f"{item['title']}\n\n{item['body']}\n\n🤖 <b>Bot:</b> @{settings.bot_username}"
    kb = _get_showcase_keyboard(settings.bot_username)

    try:
        await bot.send_message(
            chat_id=channel_id,
            text=caption,
            reply_markup=kb,
            parse_mode="HTML",
        )
        logger.info("Channel autopost successfully sent to %s", channel_id)
        return True
    except Exception as e:
        logger.exception("Failed to send channel autopost: %s", e)
        return False


async def start_autopost_scheduler(bot: Bot, interval_hours: float = 24.0) -> None:
    """Background asyncio loop running channel auto-poster every N hours."""
    logger.info("Starting Channel Auto-Poster Scheduler (interval=%.1fh)", interval_hours)
    await asyncio.sleep(10)
    while True:
        try:
            await send_channel_autopost(bot)
        except Exception as e:
            logger.exception("Error in autopost_scheduler loop: %s", e)
        await asyncio.sleep(interval_hours * 3600)
