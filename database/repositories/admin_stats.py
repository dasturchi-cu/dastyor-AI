"""Admin statistics queries."""
from __future__ import annotations

from typing import Any

from config.settings import settings
from database.connection import get_connection, row_to_dict


def _period_stats(conn, user_cond: str, pay_cond: str) -> dict[str, Any]:
    new_users = conn.execute(
        f"SELECT COUNT(*) AS c FROM users WHERE {user_cond}"
    ).fetchone()
    payments = conn.execute(
        f"SELECT COUNT(*) AS c FROM payments WHERE {pay_cond}"
    ).fetchone()
    approved = conn.execute(
        f"SELECT COUNT(*) AS c FROM payments WHERE status = 'APPROVED' AND {pay_cond}"
    ).fetchone()
    cv_count = conn.execute(
        f"SELECT COUNT(*) AS c FROM generated_files WHERE file_type = 'cv' AND {pay_cond}"
    ).fetchone()
    oby_count = conn.execute(
        f"SELECT COUNT(*) AS c FROM generated_files WHERE file_type = 'obyektivka' AND {pay_cond}"
    ).fetchone()
    approved_n = int(approved["c"]) if approved else 0
    return {
        "new_users": int(new_users["c"]) if new_users else 0,
        "payments": int(payments["c"]) if payments else 0,
        "approved_payments": approved_n,
        "cv": int(cv_count["c"]) if cv_count else 0,
        "obyektivka": int(oby_count["c"]) if oby_count else 0,
        "revenue_uzs": approved_n * settings.single_doc_price_uzs,
    }


def today_stats() -> dict[str, Any]:
    with get_connection() as conn:
        return _period_stats(
            conn,
            "date(created_at) = date('now')",
            "date(created_at) = date('now')",
        )


def top_payers(limit: int = 10) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT u.telegram_id, u.username, u.first_name, u.last_name,
                   COUNT(p.id) AS payment_count,
                   SUM(CASE WHEN p.status = 'APPROVED' THEN 1 ELSE 0 END) AS approved_count
            FROM users u
            JOIN payments p ON p.user_id = u.id
            GROUP BY u.id
            ORDER BY approved_count DESC, payment_count DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [row_to_dict(r) for r in rows if r]


def export_users_rows() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT u.telegram_id, u.username, u.first_name, u.last_name,
                   u.credits, u.is_blocked, u.created_at, u.last_active_at, u.updated_at,
                   (SELECT COUNT(*) FROM payments p WHERE p.user_id = u.id) AS payments_count,
                   (SELECT COUNT(*) FROM generated_files g
                    WHERE g.user_id = u.id AND g.file_type = 'cv') AS cv_count,
                   (SELECT COUNT(*) FROM generated_files g
                    WHERE g.user_id = u.id AND g.file_type = 'obyektivka') AS oby_count
            FROM users u
            ORDER BY u.created_at DESC
            """
        ).fetchall()
    return [row_to_dict(r) for r in rows if r]


def export_payments_rows() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT p.id, u.telegram_id, u.username, p.payer_name, p.document_type,
                   p.status, p.card_number, p.created_at, p.updated_at
            FROM payments p
            JOIN users u ON u.id = p.user_id
            ORDER BY p.created_at DESC
            """
        ).fetchall()
    return [row_to_dict(r) for r in rows if r]


def export_statistics_rows() -> list[dict[str, Any]]:
    periods = [
        ("today", "date(created_at) = date('now')", "date(created_at) = date('now')"),
        ("week", "created_at >= datetime('now', '-7 days')", "created_at >= datetime('now', '-7 days')"),
        ("month", "created_at >= datetime('now', '-30 days')", "created_at >= datetime('now', '-30 days')"),
        ("all_time", "1=1", "1=1"),
    ]
    rows: list[dict[str, Any]] = []
    with get_connection() as conn:
        for label, user_cond, pay_cond in periods:
            stats = _period_stats(conn, user_cond, pay_cond)
            stats["period"] = label
            rows.append(stats)
    return rows
