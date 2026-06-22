"""User repository."""
from __future__ import annotations

from typing import Any

from database.connection import get_connection, row_to_dict
from shared import cache as ttl_cache

_USER_TTL = 20.0


def _invalidate(telegram_id: int) -> None:
    ttl_cache.invalidate(f"user:{int(telegram_id)}")


def upsert_user(
    telegram_id: int,
    *,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> dict[str, Any]:
    tid = int(telegram_id)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (telegram_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = COALESCE(excluded.username, users.username),
                first_name = COALESCE(excluded.first_name, users.first_name),
                last_name = COALESCE(excluded.last_name, users.last_name),
                updated_at = datetime('now')
            """,
            (tid, username, first_name, last_name),
        )
        row = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (tid,)).fetchone()
    _invalidate(tid)
    data = row_to_dict(row) or {}
    if data:
        ttl_cache.set(f"user:{tid}", data, _USER_TTL)
    return data


def get_by_telegram_id(telegram_id: int) -> dict[str, Any] | None:
    tid = int(telegram_id)
    key = f"user:{tid}"
    hit = ttl_cache.get(key)
    if hit is not None:
        return hit
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (tid,)).fetchone()
    data = row_to_dict(row)
    if data:
        ttl_cache.set(key, data, _USER_TTL)
    return data


def get_by_id(user_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (int(user_id),)).fetchone()
    return row_to_dict(row)


def list_users(limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return [row_to_dict(r) for r in rows if r]


def count_users() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
    return int(row["c"]) if row else 0


def get_credits(telegram_id: int) -> int:
    user = get_by_telegram_id(telegram_id)
    return int(user.get("credits") or 0) if user else 0


def add_credits(telegram_id: int, amount: int = 1) -> int:
    tid = int(telegram_id)
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE users SET credits = credits + ?, updated_at = datetime('now')
            WHERE telegram_id = ?
            """,
            (max(0, int(amount)), tid),
        )
        row = conn.execute("SELECT credits FROM users WHERE telegram_id = ?", (tid,)).fetchone()
    _invalidate(tid)
    return int(row["credits"]) if row else 0


def consume_credit(telegram_id: int) -> bool:
    tid = int(telegram_id)
    with get_connection() as conn:
        cur = conn.execute(
            """
            UPDATE users SET credits = credits - 1, updated_at = datetime('now')
            WHERE telegram_id = ? AND credits > 0
            """,
            (tid,),
        )
        ok = cur.rowcount > 0
    if ok:
        _invalidate(tid)
    return ok
