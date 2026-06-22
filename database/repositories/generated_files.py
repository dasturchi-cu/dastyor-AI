"""Generated files repository."""
from __future__ import annotations

from typing import Any

from database.connection import get_connection, row_to_dict
from database.repositories import users as users_repo


def record_file(
    telegram_id: int,
    file_type: str,
    file_path: str,
    file_name: str | None = None,
) -> dict[str, Any] | None:
    user = users_repo.get_by_telegram_id(telegram_id)
    if not user:
        user = users_repo.upsert_user(telegram_id)
    uid = int(user["id"])
    ft = file_type.lower()
    if ft not in ("cv", "obyektivka"):
        raise ValueError("file_type must be cv or obyektivka")
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO generated_files (user_id, file_type, file_path, file_name)
            VALUES (?, ?, ?, ?)
            """,
            (uid, ft, file_path, file_name),
        )
        fid = cur.lastrowid
        row = conn.execute("SELECT * FROM generated_files WHERE id = ?", (fid,)).fetchone()
    return row_to_dict(row)


def list_by_user(telegram_id: int, limit: int = 20) -> list[dict[str, Any]]:
    user = users_repo.get_by_telegram_id(telegram_id)
    if not user:
        return []
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM generated_files
            WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
            """,
            (int(user["id"]), limit),
        ).fetchall()
    return [row_to_dict(r) for r in rows if r]


def list_all(limit: int = 50) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT g.*, u.telegram_id, u.first_name
            FROM generated_files g
            JOIN users u ON u.id = g.user_id
            ORDER BY g.created_at DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [row_to_dict(r) for r in rows if r]
