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
EMOJI_MAP: dict[str, str] = {
    "👋": "5436040291507247633",
    "🎉": "5436040291507247633",
    "🔥": "5420315771991497307",
    "💎": "5471952986970267163",
    "✨": "5472164874886846699",
    "✅": "5427009714745517609",
    "❌": "5465665476971471368",
    "💳": "5472250091332993630",
    "👇": "5470177992950946662",
    "🎁": "5199749070830197566",
    "🚀": "5445284980978621387",
    "💡": "5472146462362048818",
    "📝": "5334882760735598374",
    "⏳": "5451732530048802485",
    # 📢 (bot matnida) va 📣 (siz yuborgan) — bitta premium ID'ga
    "📢": "5469903029144657419",
    "📣": "5469903029144657419",
    "🏆": "5409008750893734809",
    # variation selector'li va oddiy variantlar — ikkalasi ham mos kelsin
    "ℹ️": "5334544901428229844",
    "ℹ": "5334544901428229844",
    "✍️": "5470060791883374114",
    "✍": "5470060791883374114",
    "🎙️": "5382013970905309819",
    "🎙": "5382013970905309819",
    "🎧": "5382013970905309819",
    "📌": "5397782960512444700",
    "⚠️": "5447644880824181073",
    "⚠": "5447644880824181073",
    "⛔️": "5280821895711697516",
    "⛔": "5280821895711697516",
    "🌐": "5352576819109308216",
    "📥": "5433811242135331842",
    "💰": "5375296873982604963",
    "👤": "5373012449597335010",
    "📊": "5431577498364158238",
    "🔄": "5264727218734524899",
    "📄": "5334882760735598374",
    "📁": "5433811242135331842",
    "🔙": "5264727218734524899",
    "1️⃣": "5235776368905562305",
    "2️⃣": "5237704680372447424",
    "3️⃣": "5238044171767393675",
    "📤": "5433614747381538714",
    "👍": "5427009714745517609",
    "⚡": "5420315771991497307",
    "⚡️": "5420315771991497307",
}


async def safe_react(message: Any, emoji: str = "⚡") -> None:
    """Set reaction (e.g. ⚡, ✍️, 🎙, 👍, 🌐) on user message silently if supported."""
    if not message or not hasattr(message, "react"):
        return
    try:
        from aiogram.types import ReactionTypeEmoji

        # Clean variation selector for standard emoji reactions
        clean_emoji = emoji.replace("\ufe0f", "")
        await message.react([ReactionTypeEmoji(emoji=clean_emoji)])
    except Exception:
        pass




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


def leading_emoji_id(text: str | None) -> str | None:
    """Matn boshidagi emoji uchun custom_emoji_id (Bot API 9.4 tugma iconi).

    Tugma matnining eng boshida turgan mos emojini topadi. Topilmasa None.
    """
    if not text or _pattern is None:
        return None
    m = _pattern.match(text)
    if m:
        return EMOJI_MAP[m.group(0)]
    return None


_GENERIC_LEADING_EMOJI_RE = re.compile(
    r"^(?:[\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff\u2b50\u2b55\u203c\u2049\u2139\u2122]|\ufe0f|\u200d|\u20e3)+\s*"
)


def strip_leading_emoji(text: str | None) -> str:
    """Matn boshidagi oddiy unicode emojini olib tashlaydi (tugmada takrorlanmasligi uchun)."""
    if not text:
        return ""
    if _pattern is not None:
        m = _pattern.match(text)
        if m:
            return text[len(m.group(0)) :].lstrip()
    return _GENERIC_LEADING_EMOJI_RE.sub("", text).lstrip()



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
