"""Persist Telegram users to SQLite on every bot update."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from database.repositories import users as users_repo
from shared.async_db import run as db_run


class UserPersistenceMiddleware(BaseMiddleware):
    """Upsert sender to SQLite before handlers run — not only on /start."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: User | None = data.get("event_from_user")
        if tg_user and tg_user.id:
            await db_run(
                users_repo.upsert_user,
                tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
            )
        return await handler(event, data)
