"""Required channels repository — mandatory subscription management."""
from __future__ import annotations

import time
from typing import Any

from database.connection import get_connection

# In-memory cache: channel list (5 second TTL)
_CACHE: dict[str, Any] = {"channels": None, "ts": 0.0}
_CACHE_TTL = 5.0


def _invalidate() -> None:
    _CACHE["ts"] = 0.0


def get_active_channels() -> list[dict]:
    """Return all active required channels (cached)."""
    now = time.monotonic()
    if _CACHE["channels"] is not None and now - float(_CACHE["ts"]) < _CACHE_TTL:
        return _CACHE["channels"]  # type: ignore[return-value]

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, channel_id, title, invite_link, is_active, created_at
            FROM required_channels
            WHERE is_active = 1
            ORDER BY id
            """
        ).fetchall()
    result = [dict(r) for r in rows]
    _CACHE["channels"] = result
    _CACHE["ts"] = now
    return result


def add_channel(
    channel_id: str,
    *,
    title: str = "",
    invite_link: str = "",
    added_by: int | None = None,
) -> int:
    """Add or re-activate a required channel. Returns row id."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO required_channels (channel_id, title, invite_link, is_active, added_by)
            VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(channel_id) DO UPDATE SET
                title = excluded.title,
                invite_link = excluded.invite_link,
                is_active = 1,
                added_by = excluded.added_by
            """,
            (channel_id, title or "", invite_link or "", added_by),
        )
        row = conn.execute(
            "SELECT id FROM required_channels WHERE channel_id = ?", (channel_id,)
        ).fetchone()
    _invalidate()
    return int(row["id"]) if row else 0


def remove_channel(channel_id: str) -> bool:
    """Deactivate a required channel. Returns True if found."""
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE required_channels SET is_active = 0 WHERE channel_id = ?",
            (channel_id,),
        )
    _invalidate()
    return cur.rowcount > 0


def remove_channel_by_id(row_id: int) -> bool:
    """Deactivate a required channel by DB id."""
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE required_channels SET is_active = 0 WHERE id = ?",
            (row_id,),
        )
    _invalidate()
    return cur.rowcount > 0


def get_all_channels() -> list[dict]:
    """Return ALL channels including inactive (for admin listing)."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, channel_id, title, invite_link, is_active, created_at
            FROM required_channels
            ORDER BY is_active DESC, id
            """
        ).fetchall()
    return [dict(r) for r in rows]
