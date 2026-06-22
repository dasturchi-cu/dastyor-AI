"""Error log repository for admin panel."""
from __future__ import annotations

from typing import Any

from database.connection import get_connection, row_to_dict


def record(category: str, message: str, details: str | None = None) -> None:
    cat = (category or "general").strip().lower()[:32]
    msg = (message or "")[:2000]
    det = (details or "")[:4000] or None
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO error_logs (category, message, details) VALUES (?, ?, ?)",
            (cat, msg, det),
        )


def list_recent(limit: int = 20, category: str | None = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if category:
            rows = conn.execute(
                """
                SELECT * FROM error_logs
                WHERE category = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (category.lower(), limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM error_logs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [row_to_dict(r) for r in rows if r]


def count_by_category(category: str) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM error_logs WHERE category = ?",
            (category.lower(),),
        ).fetchone()
    return int(row["c"]) if row else 0
