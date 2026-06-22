"""Live activity feed for admin dashboard."""
from __future__ import annotations

from typing import Any

from database.connection import get_connection, row_to_dict
from shared import cache as ttl_cache

_FEED_TTL = 3.0
_DASH_CACHE_KEY = "admin:dashboard"


def record(
    event_type: str,
    *,
    actor_name: str = "",
    telegram_id: int | None = None,
    detail: str = "",
) -> None:
    et = (event_type or "other").strip().lower()[:32]
    name = (actor_name or "").strip()[:120]
    det = (detail or "").strip()[:200]
    user_id = None
    if telegram_id:
        from database.repositories import users as users_repo

        user = users_repo.get_by_telegram_id(int(telegram_id))
        if user:
            user_id = int(user["id"])
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO activity_events (event_type, user_id, actor_name, detail)
            VALUES (?, ?, ?, ?)
            """,
            (et, user_id, name or None, det or None),
        )
    ttl_cache.invalidate(_DASH_CACHE_KEY)


def list_recent(limit: int = 8) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT event_type, actor_name, detail, created_at
            FROM activity_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(1, int(limit)),),
        ).fetchall()
    return [row_to_dict(r) for r in rows if r]


def prune_old(keep: int = 500) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            DELETE FROM activity_events
            WHERE id NOT IN (
                SELECT id FROM activity_events ORDER BY id DESC LIMIT ?
            )
            """,
            (max(50, int(keep)),),
        )
