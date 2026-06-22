"""Obyektivka data persistence repository."""
from __future__ import annotations

import json
from typing import Any

from database.connection import get_connection, row_to_dict
from database.repositories import users as users_repo


def save_payload(telegram_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    user = users_repo.upsert_user(telegram_id)
    uid = int(user["id"])
    blob = json.dumps(payload, ensure_ascii=False)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO obyektivka_data (user_id, payload, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                payload = excluded.payload,
                updated_at = datetime('now')
            """,
            (uid, blob),
        )
        row = conn.execute("SELECT * FROM obyektivka_data WHERE user_id = ?", (uid,)).fetchone()
    return row_to_dict(row) or {}


def save_pending(telegram_id: int, payload: dict[str, Any]) -> None:
    user = users_repo.upsert_user(telegram_id)
    uid = int(user["id"])
    blob = json.dumps(payload, ensure_ascii=False)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO obyektivka_data (user_id, payload, pending_payload, updated_at)
            VALUES (?, '{}', ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                pending_payload = excluded.pending_payload,
                updated_at = datetime('now')
            """,
            (uid, blob),
        )


def get_pending(telegram_id: int) -> dict[str, Any] | None:
    user = users_repo.get_by_telegram_id(telegram_id)
    if not user:
        return None
    with get_connection() as conn:
        row = conn.execute(
            "SELECT pending_payload, payload FROM obyektivka_data WHERE user_id = ?",
            (int(user["id"]),),
        ).fetchone()
    if not row:
        return None
    raw = row["pending_payload"] or row["payload"]
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def get_payload(telegram_id: int) -> dict[str, Any] | None:
    user = users_repo.get_by_telegram_id(telegram_id)
    if not user:
        return None
    with get_connection() as conn:
        row = conn.execute(
            "SELECT payload FROM obyektivka_data WHERE user_id = ?",
            (int(user["id"]),),
        ).fetchone()
    if not row or not row["payload"]:
        return None
    try:
        data = json.loads(row["payload"])
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def clear_pending(telegram_id: int) -> None:
    user = users_repo.get_by_telegram_id(telegram_id)
    if not user:
        return
    with get_connection() as conn:
        conn.execute(
            "UPDATE obyektivka_data SET pending_payload = NULL WHERE user_id = ?",
            (int(user["id"]),),
        )
