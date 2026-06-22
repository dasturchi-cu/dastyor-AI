"""Admin action audit log."""
from __future__ import annotations

from typing import Any

from database.connection import get_connection, row_to_dict


def record(admin_id: int, action: str, details: str | None = None) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO admin_logs (admin_id, action, details)
            VALUES (?, ?, ?)
            """,
            (int(admin_id), action.strip()[:120], (details or "")[:2000] or None),
        )


def list_recent(limit: int = 30) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM admin_logs ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [row_to_dict(r) for r in rows if r]
