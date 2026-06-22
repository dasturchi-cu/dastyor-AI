"""User repository — SQLite is the single source of truth."""
from __future__ import annotations

from typing import Any

from database.connection import get_connection, row_to_dict


def invalidate_cache(telegram_id: int) -> None:
    """Backward-compatible no-op (in-memory user cache removed)."""
    del telegram_id


def _exists_in_db(telegram_id: int) -> bool:
    tid = int(telegram_id)
    with get_connection() as conn:
        row = conn.execute("SELECT 1 FROM users WHERE telegram_id = ?", (tid,)).fetchone()
    return row is not None


def upsert_user(
    telegram_id: int,
    *,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> dict[str, Any]:
    tid = int(telegram_id)
    existed = _exists_in_db(tid)
    full_name = " ".join(filter(None, [first_name, last_name])).strip() or None
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (
                telegram_id, username, first_name, last_name, full_name,
                first_seen_at, last_seen_at, last_active_at
            )
            VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'), datetime('now'))
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = COALESCE(excluded.username, users.username),
                first_name = COALESCE(excluded.first_name, users.first_name),
                last_name = COALESCE(excluded.last_name, users.last_name),
                full_name = COALESCE(
                    excluded.full_name,
                    TRIM(COALESCE(excluded.first_name, users.first_name, '') || ' '
                         || COALESCE(excluded.last_name, users.last_name, '')),
                    users.full_name
                ),
                last_seen_at = datetime('now'),
                last_active_at = datetime('now'),
                updated_at = datetime('now')
            """,
            (tid, username, first_name, last_name, full_name),
        )
        row = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (tid,)).fetchone()
    data = row_to_dict(row) or {}
    if not existed and data:
        from shared.activity import log_register

        name = " ".join(filter(None, [first_name, last_name])).strip() or "Foydalanuvchi"
        log_register(tid, name)
    return data


def get_by_telegram_id(telegram_id: int) -> dict[str, Any] | None:
    tid = int(telegram_id)
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (tid,)).fetchone()
    return row_to_dict(row)


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
    return ok


def is_blocked(telegram_id: int) -> bool:
    user = get_by_telegram_id(telegram_id)
    return bool(int(user.get("is_blocked") or 0)) if user else False


def set_blocked(telegram_id: int, blocked: bool) -> bool:
    tid = int(telegram_id)
    with get_connection() as conn:
        cur = conn.execute(
            """
            UPDATE users SET is_blocked = ?, updated_at = datetime('now')
            WHERE telegram_id = ?
            """,
            (1 if blocked else 0, tid),
        )
        ok = cur.rowcount > 0
    return ok


def remove_credits(telegram_id: int, amount: int = 1) -> int:
    tid = int(telegram_id)
    amount = max(0, int(amount))
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE users
            SET credits = CASE WHEN credits >= ? THEN credits - ? ELSE 0 END,
                updated_at = datetime('now')
            WHERE telegram_id = ?
            """,
            (amount, amount, tid),
        )
        row = conn.execute("SELECT credits FROM users WHERE telegram_id = ?", (tid,)).fetchone()
    return int(row["credits"]) if row else 0


def search_users(query: str, limit: int = 10) -> list[dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return []
    with get_connection() as conn:
        if q.isdigit():
            rows = conn.execute(
                """
                SELECT * FROM users
                WHERE CAST(telegram_id AS TEXT) LIKE ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (f"%{q}%", limit),
            ).fetchall()
        else:
            term = q.lstrip("@").strip()
            like = f"%{term}%"
            rows = conn.execute(
                """
                SELECT * FROM users
                WHERE username LIKE ? COLLATE NOCASE
                   OR first_name LIKE ? COLLATE NOCASE
                   OR last_name LIKE ? COLLATE NOCASE
                   OR (first_name || ' ' || COALESCE(last_name, '')) LIKE ? COLLATE NOCASE
                ORDER BY created_at DESC LIMIT ?
                """,
                (like, like, like, like, limit),
            ).fetchall()
    return [row_to_dict(r) for r in rows if r]


def list_broadcast_targets() -> list[int]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT telegram_id FROM users WHERE is_blocked = 0 ORDER BY id"
        ).fetchall()
    return [int(r["telegram_id"]) for r in rows if r]


def get_profile_stats(telegram_id: int) -> dict[str, Any] | None:
    user = get_by_telegram_id(telegram_id)
    if not user:
        return None
    uid = int(user["id"])
    with get_connection() as conn:
        cv_row = conn.execute(
            "SELECT COUNT(*) AS c FROM generated_files WHERE user_id = ? AND file_type = 'cv'",
            (uid,),
        ).fetchone()
        oby_row = conn.execute(
            """
            SELECT COUNT(*) AS c FROM generated_files
            WHERE user_id = ? AND file_type = 'obyektivka'
            """,
            (uid,),
        ).fetchone()
        pay_row = conn.execute(
            "SELECT COUNT(*) AS c FROM payments WHERE user_id = ?",
            (uid,),
        ).fetchone()
    return {
        **user,
        "cv_count": int(cv_row["c"]) if cv_row else 0,
        "obyektivka_count": int(oby_row["c"]) if oby_row else 0,
        "payments_count": int(pay_row["c"]) if pay_row else 0,
        "last_activity": user.get("last_active_at") or user.get("updated_at"),
    }
