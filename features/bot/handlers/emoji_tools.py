"""Premium emoji ID topish vositasi (faqat admin).

Admin `/emojiid` bilan birga premium emojilarni yuboradi (yoki premium
emojili xabarga reply qiladi) — bot har bir emoji uchun ``custom_emoji_id``
ni topib, ``shared/premium_emoji.py`` ga tayyor ko'chirib qo'yiladigan
ko'rinishda qaytaradi.
"""
from __future__ import annotations

import html

from aiogram import Router
from aiogram.enums import MessageEntityType
from aiogram.filters import Command
from aiogram.types import Message, MessageEntity

from shared.auth import is_admin

router = Router()


def _slice_utf16(text: str, offset: int, length: int) -> str:
    """Telegram entity offset/length UTF-16 kod birliklarida beriladi."""
    data = text.encode("utf-16-le")
    return data[offset * 2 : (offset + length) * 2].decode("utf-16-le")


def _collect(message: Message) -> list[tuple[str, str]]:
    """(emoji, custom_emoji_id) juftliklarini yig'adi."""
    pairs: list[tuple[str, str]] = []
    for src in (message, message.reply_to_message):
        if not src:
            continue
        text = src.text or src.caption or ""
        entities: list[MessageEntity] = src.entities or src.caption_entities or []
        for ent in entities:
            if ent.type == MessageEntityType.CUSTOM_EMOJI and ent.custom_emoji_id:
                emoji = _slice_utf16(text, ent.offset, ent.length)
                pairs.append((emoji, ent.custom_emoji_id))
    return pairs


@router.message(Command("emojiid"))
async def cmd_emojiid(message: Message) -> None:
    uid = message.from_user.id if message.from_user else None
    if not is_admin(uid):
        return  # jimgina — oddiy foydalanuvchiga ko'rinmaydi

    pairs = _collect(message)
    if not pairs:
        await message.answer(
            "💡 <b>Premium emoji ID topish</b>\n\n"
            "Premium (animatsion) emojilarni shu buyruq bilan yuboring:\n"
            "<code>/emojiid 🔥💎✨</code>\n\n"
            "Yoki premium emojili istalgan xabarga <b>reply</b> qilib "
            "<code>/emojiid</code> yozing.\n\n"
            "⚠️ Oddiy emoji emas — Premium klaviaturadagi maxsus emojini tanlang."
        )
        return

    # Takrorlarni olib tashlash (tartibni saqlab).
    seen: dict[str, str] = {}
    for emoji, eid in pairs:
        seen.setdefault(emoji, eid)

    lines = [f'    "{e}": "{eid}",' for e, eid in seen.items()]
    dict_block = "EMOJI_MAP = {\n" + "\n".join(lines) + "\n}"

    human = "\n".join(f"{html.escape(e)} → <code>{eid}</code>" for e, eid in seen.items())

    await message.answer(
        f"✅ <b>{len(seen)} ta premium emoji topildi:</b>\n\n"
        f"{human}\n\n"
        "👇 Quyidagini <code>shared/premium_emoji.py</code> dagi "
        "<code>EMOJI_MAP</code> ga qo'ying:"
    )
    await message.answer(f"<pre>{html.escape(dict_block)}</pre>")
