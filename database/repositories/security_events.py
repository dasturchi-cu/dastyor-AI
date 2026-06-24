"""Security audit events repository."""
from __future__ import annotations

from typing import Any

from database.connection import get_connection, row_to_dict


def record(
    *,
    event_type: str,
    severity: str = "info",
    ip: str | None = None,
    user_id: int | None = None,
    details: str | None = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO security_events (event_type, severity, ip, user_id, details)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                event_type.strip()[:80],
                severity.strip()[:20],
                (ip or "")[:64] or None,
                int(user_id) if user_id else None,
                (details or "")[:2000] or None,
            ),
        )


def count_since(event_type: str, hours: int = 24) -> int:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) FROM security_events
            WHERE event_type = ?
              AND datetime(created_at) >= datetime('now', ?)
            """,
            (event_type, f"-{int(hours)} hours"),
        ).fetchone()
    return int(row[0]) if row else 0


def count_by_severity(severity: str, hours: int = 24) -> int:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) FROM security_events
            WHERE severity = ?
              AND datetime(created_at) >= datetime('now', ?)
            """,
            (severity, f"-{int(hours)} hours"),
        ).fetchone()
    return int(row[0]) if row else 0


def list_recent(limit: int = 30, *, event_type: str | None = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if event_type:
            rows = conn.execute(
                """
                SELECT * FROM security_events
                WHERE event_type = ?
                ORDER BY id DESC LIMIT ?
                """,
                (event_type, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM security_events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [row_to_dict(r) for r in rows if r]


def top_ips(hours: int = 24, limit: int = 10) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT ip, COUNT(*) AS hits
            FROM security_events
            WHERE ip IS NOT NULL AND ip != ''
              AND datetime(created_at) >= datetime('now', ?)
            GROUP BY ip
            ORDER BY hits DESC
            LIMIT ?
            """,
            (f"-{int(hours)} hours", limit),
        ).fetchall()
    return [{"ip": r[0], "hits": int(r[1])} for r in rows if r]
