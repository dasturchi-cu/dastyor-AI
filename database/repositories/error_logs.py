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
    from shared.error_log import is_noise_error

    fetch = max(limit * 5, 40)
    with get_connection() as conn:
        if category:
            rows = conn.execute(
                """
                SELECT * FROM error_logs
                WHERE category = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (category.lower(), fetch),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM error_logs ORDER BY created_at DESC LIMIT ?",
                (fetch,),
            ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        item = row_to_dict(row)
        if not item:
            continue
        if is_noise_error(
            str(item.get("category") or ""),
            str(item.get("message") or ""),
            str(item.get("details") or "") or None,
        ):
            continue
        out.append(item)
        if len(out) >= limit:
            break
    return out


def count_by_category(category: str) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM error_logs WHERE category = ?",
            (category.lower(),),
        ).fetchone()
    return int(row["c"]) if row else 0
