"""Premium (custom) emoji qo'llab-quvvatlash.

Telegram qoidasi: bot custom (premium/animatsion) emoji yubora oladi, agar
bot egasida Telegram Premium obunasi bo'lsa (yoki Fragment'da username sotib
olingan bo'lsa). Bu modul oddiy emojilarni `<tg-emoji>` HTML teglariga
almashtiradi — faqat HTML parse mode bilan ishlaydi.

Ishlatish:
1. Admin `/emojiid 🔥💎` yuboradi → bot har bir emoji uchun custom_emoji_id qaytaradi.
2. Olingan ID'larni pastdagi ``EMOJI_MAP`` ga qo'shasiz.
3. Chiqadigan barcha xabarlar avtomatik premium emoji bilan yuboriladi
   (bot session middleware orqali, ``main.create_bot`` da ulangan).

``EMOJI_MAP`` bo'sh bo'lsa modul hech narsa qilmaydi (bot normal ishlaydi).
"""
from __future__ import annotations

import html
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram import Bot
    from aiogram.client.session.middlewares.base import NextRequestMiddlewareType
    from aiogram.methods import Response, TelegramMethod
    from aiogram.methods.base import TelegramType

# Oddiy emoji  ->  custom_emoji_id (satr sifatida).
# ID'larni /emojiid buyrug'i orqali oling va shu yerga qo' shing.
# Namuna:
#   EMOJI_MAP = {
#       "🔥": "5424818369356124161",
#       "💎": "5420216386448270341",
#   }
EMOJI_MAP: dict[str, str] = {}


def _build_pattern() -> re.Pattern[str] | None:
    if not EMOJI_MAP:
        return None
    # Uzunroq ketma-ketliklar birinchi mos kelsin (masalan, ZWJ emojilar).
    keys = sorted(EMOJI_MAP, key=len, reverse=True)
    return re.compile("|".join(re.escape(k) for k in keys))


_pattern = _build_pattern()


def reload_pattern() -> None:
    """EMOJI_MAP dinamik o'zgartirilsa qayta qurish uchun."""
    global _pattern
    _pattern = _build_pattern()


def premiumize(text: str | None) -> str | None:
    """Matndagi mos emojilarni `<tg-emoji>` teglariga almashtiradi.

    Xarita bo'sh bo'lsa yoki mos emoji bo'lmasa — matn o'zgarishsiz qaytadi.
    HTML parse mode talab qilinadi (loyihada default HTML).
    """
    if not text or _pattern is None:
        return text

    def _repl(m: re.Match[str]) -> str:
        emoji = m.group(0)
        emoji_id = EMOJI_MAP[emoji]
        # Emoji fallback matni HTML-escape qilinadi (Premium bo'lmagan
        # ko'rinishda oddiy emoji ko'rinadi).
        return f'<tg-emoji emoji-id="{emoji_id}">{html.escape(emoji)}</tg-emoji>'

    return _pattern.sub(_repl, text)


def has_mapping() -> bool:
    return bool(EMOJI_MAP)


def _parse_mode_ok(method: Any) -> bool:
    """Faqat HTML parse mode uchun tg-emoji ishlaydi.

    aiogram'da o'rnatilmagan parse_mode `Default` sentinel bo'ladi va bot
    default'iga (loyihada HTML) tushadi — bunda ruxsat beramiz. Aniq
    MarkdownV2/Markdown o'rnatilgan bo'lsa — o'tkazib yuboramiz.
    """
    pm = getattr(method, "parse_mode", None)
    if isinstance(pm, str):
        return pm.upper() == "HTML"
    # None yoki Default sentinel -> bot default (HTML)
    return True


class PremiumEmojiMiddleware:
    """Bot session middleware — chiqadigan text/caption'ni premiumize qiladi.

    ``bot.session.middleware(...)`` orqali ulanadi, shuning uchun polling va
    webhook rejimlarida ham barcha yuboriladigan xabarlarga qo'llanadi.
    """

    async def __call__(
        self,
        make_request: "NextRequestMiddlewareType[TelegramType]",
        bot: "Bot",
        method: "TelegramMethod[TelegramType]",
    ) -> "Response[TelegramType]":
        if _pattern is not None and _parse_mode_ok(method):
            for attr in ("text", "caption"):
                value = getattr(method, attr, None)
                if isinstance(value, str) and value:
                    new_value = premiumize(value)
                    if new_value != value:
                        setattr(method, attr, new_value)
        return await make_request(bot, method)
