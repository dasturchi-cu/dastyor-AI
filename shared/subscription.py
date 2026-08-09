"""Mandatory subscription check service.

Checks if a Telegram user is a member of all required channels.
Returns list of channels the user is NOT subscribed to.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from database.repositories import required_channels as channels_repo

if TYPE_CHECKING:
    from aiogram import Bot

logger = logging.getLogger(__name__)


async def get_unsubscribed_channels(bot: "Bot", user_id: int) -> list[dict]:
    """
    Returns list of channel dicts the user is NOT a member of.
    Empty list means user is subscribed to all required channels.
    """
    channels = channels_repo.get_active_channels()
    if not channels:
        return []

    unsubscribed = []
    for ch in channels:
        channel_id = ch["channel_id"]
        try:
            member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status in ("left", "kicked", "banned"):
                unsubscribed.append(ch)
        except Exception as exc:
            logger.warning(
                "Subscription check failed for channel %s user %s: %s",
                channel_id,
                user_id,
                exc,
            )
            # If we can't check (bot not admin), skip this channel
            continue

    return unsubscribed


def build_subscribe_keyboard(unsubscribed: list[dict]) -> dict:
    """Build InlineKeyboardMarkup with subscribe buttons + check button."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    rows = []
    for ch in unsubscribed:
        title = ch.get("title") or ch["channel_id"]
        invite_link = ch.get("invite_link") or ""
        channel_id = ch["channel_id"]

        # Use invite_link if available, else build t.me link
        if invite_link:
            url = invite_link
        elif channel_id.startswith("@"):
            url = f"https://t.me/{channel_id.lstrip('@')}"
        else:
            url = f"https://t.me/c/{str(channel_id).lstrip('-100')}/1"

        rows.append(
            [InlineKeyboardButton(text=f"📢 {title} ga obuna bo'lish", url=url)]
        )

    rows.append(
        [InlineKeyboardButton(text="✅ Obuna bo'ldim", callback_data="sub_check")]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_subscribe_text(unsubscribed: list[dict]) -> str:
    lines = ["📢 <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:</b>\n"]
    for i, ch in enumerate(unsubscribed, 1):
        title = ch.get("title") or ch["channel_id"]
        lines.append(f"{i}. <b>{title}</b>")
    lines.append(
        "\n👇 Obuna bo'lgandan so'ng <b>«✅ Obuna bo'ldim»</b> tugmasini bosing."
    )
    return "\n".join(lines)
