"""Support messages repository."""
from __future__ import annotations

from typing import Any

from database.connection import get_connection, row_to_dict
from database.repositories import users as users_repo


def create_message(telegram_id: int, message: str) -> dict[str, Any] | None:
    user = users_repo.upsert_user(telegram_id)
    uid = int(user["id"])
    text = (message or "").strip()[:4000]
    if not text:
        return None
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO support_messages (user_id, message, status)
            VALUES (?, ?, 'open')
            """,
            (uid, text),
        )
        row = conn.execute(
            "SELECT * FROM support_messages WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return row_to_dict(row)


def set_reply(message_id: int, admin_reply: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            """
            UPDATE support_messages
            SET admin_reply = ?, status = 'replied'
            WHERE id = ?
            """,
            (admin_reply.strip()[:4000], int(message_id)),
        )
        return cur.rowcount > 0


def list_open(limit: int = 30) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT s.*, u.telegram_id, u.username, u.first_name
            FROM support_messages s
            JOIN users u ON u.id = s.user_id
            WHERE s.status = 'open'
            ORDER BY s.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [row_to_dict(r) for r in rows if r]


def count_open() -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM support_messages WHERE status = 'open'"
        ).fetchone()
    return int(row["c"]) if row else 0
