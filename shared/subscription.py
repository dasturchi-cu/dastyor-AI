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


async def ensure_user_subscribed_api(request, uid: int | None) -> None:
    """Check subscription on REST API endpoints — raise HTTP 403 if unsubscribed."""
    if not uid:
        return
    from shared.auth import is_admin
    if is_admin(uid):
        return

    bot_app = getattr(getattr(request, "app", None), "state", None)
    bot_obj = getattr(bot_app, "bot", None) if bot_app else None
    if not bot_obj:
        return

    try:
        unsubscribed = await get_unsubscribed_channels(bot_obj, uid)
        if unsubscribed:
            channels_info = []
            for ch in unsubscribed:
                cid = str(ch["channel_id"])
                link = ch.get("invite_link") or (f"https://t.me/{cid.lstrip('@')}" if cid.startswith("@") else "")
                channels_info.append({"title": ch.get("title") or cid, "link": link, "channel_id": cid})

            from fastapi import HTTPException
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "subscription_required",
                    "message": "📢 Botdan foydalanish uchun rasmiy kanalimizga obuna bo'ling!",
                    "channels": channels_info,
                },
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("ensure_user_subscribed_api check error: %s", exc)
