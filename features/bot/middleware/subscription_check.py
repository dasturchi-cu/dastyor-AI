"""Subscription check middleware.

Intercepts every bot update and verifies the user is subscribed
to all required channels. If not, shows subscribe buttons and stops
further processing.

Admin users are exempt from the subscription check.
"""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User

from config.settings import settings
from shared.subscription import (
    build_subscribe_keyboard,
    build_subscribe_text,
    get_unsubscribed_channels,
)

logger = logging.getLogger(__name__)

# Callbacks that are always allowed (so user can click "I subscribed" button)
_ALWAYS_ALLOWED_CALLBACKS = {"sub_check"}


def _is_admin(user_id: int) -> bool:
    """Check if user is an admin — admins bypass subscription check."""
    from features.admin.dispatch import is_admin
    return is_admin(user_id)


class SubscriptionCheckMiddleware(BaseMiddleware):
    """Block users who are not subscribed to required channels."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await self._check(handler, event, data)
        except Exception as exc:
            logger.error("SubscriptionCheckMiddleware critical error: %s", exc, exc_info=True)
            return await handler(event, data)

    async def _check(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: User | None = data.get("event_from_user")
        if not tg_user or not tg_user.id:
            return await handler(event, data)

        user_id = tg_user.id

        # Admins are exempt
        if _is_admin(user_id):
            return await handler(event, data)

        # Extract Message / CallbackQuery from Update or Event
        event_obj = getattr(event, "event", event)
        msg: Message | None = None
        cb: CallbackQuery | None = None

        if isinstance(event_obj, Message):
            msg = event_obj
        elif isinstance(event_obj, CallbackQuery):
            cb = event_obj
        elif hasattr(event, "message") and getattr(event, "message", None):
            msg = getattr(event, "message")
        elif hasattr(event, "callback_query") and getattr(event, "callback_query", None):
            cb = getattr(event, "callback_query")

        # Always allow "I subscribed" callback
        if cb and (getattr(cb, "data", "") or "") in _ALWAYS_ALLOWED_CALLBACKS:
            return await handler(event, data)

        bot = data.get("bot")
        if bot is None:
            return await handler(event, data)

        try:
            unsubscribed = await get_unsubscribed_channels(bot, user_id)
        except Exception as exc:
            logger.warning("Subscription check failed: %s", exc)
            return await handler(event, data)

        if not unsubscribed:
            return await handler(event, data)

        # User is not subscribed — send prompt with channel links and STOP handler
        text = build_subscribe_text(unsubscribed)
        keyboard = build_subscribe_keyboard(unsubscribed)

        try:
            if msg:
                await msg.answer(text, reply_markup=keyboard)
            elif cb:
                await cb.answer("⚠️ Avval kanallarga obuna bo'ling!", show_alert=True)
                if cb.message:
                    try:
                        await cb.message.answer(text, reply_markup=keyboard)
                    except Exception:
                        pass
        except Exception as exc:
            logger.warning("Subscription prompt error: %s", exc)

        return None
