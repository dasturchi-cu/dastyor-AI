"""AI sessions repository."""
from __future__ import annotations

import json
from typing import Any

from database.connection import get_connection, row_to_dict
from database.repositories import users as users_repo


def create_session(
    telegram_id: int,
    session_type: str,
    transcript: str | None = None,
    extracted_data: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    user = users_repo.upsert_user(telegram_id)
    uid = int(user["id"])
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO ai_sessions (user_id, session_type, transcript, extracted_data, status)
            VALUES (?, ?, ?, ?, 'active')
            """,
            (
                uid,
                session_type,
                transcript,
                json.dumps(extracted_data, ensure_ascii=False) if extracted_data else None,
            ),
        )
        sid = cur.lastrowid
        row = conn.execute("SELECT * FROM ai_sessions WHERE id = ?", (sid,)).fetchone()
    return row_to_dict(row)


def get_latest(telegram_id: int, session_type: str) -> dict[str, Any] | None:
    user = users_repo.get_by_telegram_id(telegram_id)
    if not user:
        return None
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM ai_sessions
            WHERE user_id = ? AND session_type = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (int(user["id"]), session_type),
        ).fetchone()
    if not row:
        return None
    data = row_to_dict(row)
    if data and data.get("extracted_data"):
        try:
            data["extracted_data"] = json.loads(data["extracted_data"])
        except json.JSONDecodeError:
            pass
    return data
