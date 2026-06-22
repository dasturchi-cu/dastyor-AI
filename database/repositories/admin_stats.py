"""Admin dashboard snapshot — optimized single-connection queries."""
from __future__ import annotations

from typing import Any

from config.settings import settings
from database.connection import get_connection, row_to_dict
from shared import cache as ttl_cache

_DASH_KEY = "admin:dashboard"
_DASH_TTL = 4.0


def dashboard_snapshot() -> dict[str, Any]:
    hit = ttl_cache.get(_DASH_KEY)
    if hit is not None:
        return hit

    online_m = max(1, settings.online_user_minutes)
    inactive_d = max(1, settings.inactive_user_days)

    with get_connection() as conn:
        today = _period_stats(
            conn,
            "date(created_at) = date('now')",
            "date(created_at) = date('now')",
        )
        online = conn.execute(
            f"""
            SELECT COUNT(*) AS c FROM users
            WHERE datetime(COALESCE(last_active_at, updated_at))
                  >= datetime('now', '-{online_m} minutes')
            """
        ).fetchone()
        active = conn.execute(
            """
            SELECT COUNT(*) AS c FROM users
            WHERE date(COALESCE(last_active_at, updated_at)) = date('now')
            """
        ).fetchone()
        inactive = conn.execute(
            f"""
            SELECT COUNT(*) AS c FROM users
            WHERE datetime(COALESCE(last_active_at, updated_at))
                  < datetime('now', '-{inactive_d} days')
            """
        ).fetchone()
        pending = conn.execute(
            "SELECT COUNT(*) AS c FROM payments WHERE status = 'PENDING'"
        ).fetchone()
        total_users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
        paid_users = conn.execute(
            """
            SELECT COUNT(DISTINCT user_id) AS c FROM payments
            WHERE status = 'APPROVED'
            """
        ).fetchone()
        cv_total = conn.execute(
            "SELECT COUNT(*) AS c FROM generated_files WHERE file_type = 'cv'"
        ).fetchone()
        oby_total = conn.execute(
            "SELECT COUNT(*) AS c FROM generated_files WHERE file_type = 'obyektivka'"
        ).fetchone()
        top_rows = conn.execute(
            """
            SELECT u.username, u.first_name, u.last_name,
                   SUM(CASE WHEN p.status = 'APPROVED' THEN 1 ELSE 0 END) AS approved_count
            FROM users u
            JOIN payments p ON p.user_id = u.id
            GROUP BY u.id
            HAVING approved_count > 0
            ORDER BY approved_count DESC
            LIMIT 3
            """
        ).fetchall()
        feed_rows = conn.execute(
            """
            SELECT event_type, actor_name, detail, created_at
            FROM activity_events
            ORDER BY id DESC
            LIMIT 8
            """
        ).fetchall()

    total_n = int(total_users["c"]) if total_users else 0
    paid_n = int(paid_users["c"]) if paid_users else 0
    conversion = round((paid_n / total_n) * 100, 1) if total_n else 0.0

    data: dict[str, Any] = {
        **today,
        "online_users": int(online["c"]) if online else 0,
        "today_users": today.get("new_users", 0),
        "active_users": int(active["c"]) if active else 0,
        "inactive_users": int(inactive["c"]) if inactive else 0,
        "pending_payments": int(pending["c"]) if pending else 0,
        "total_users": total_n,
        "paid_users": paid_n,
        "conversion_pct": conversion,
        "cv_total": int(cv_total["c"]) if cv_total else 0,
        "obyektivka_total": int(oby_total["c"]) if oby_total else 0,
        "top_users": [row_to_dict(r) for r in top_rows if r],
        "feed": [row_to_dict(r) for r in feed_rows if r],
    }
    ttl_cache.set(_DASH_KEY, data, _DASH_TTL)
    return data


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
        stats = _period_stats(
            conn,
            "date(created_at) = date('now')",
            "date(created_at) = date('now')",
        )
        active = conn.execute(
            """
            SELECT COUNT(*) AS c FROM users
            WHERE date(COALESCE(last_active_at, updated_at)) = date('now')
            """
        ).fetchone()
        pending = conn.execute(
            "SELECT COUNT(*) AS c FROM payments WHERE status = 'PENDING'"
        ).fetchone()
        total_users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
        paid_users = conn.execute(
            "SELECT COUNT(DISTINCT user_id) AS c FROM payments WHERE status = 'APPROVED'"
        ).fetchone()
        stats["active_users"] = int(active["c"]) if active else 0
        stats["pending_payments"] = int(pending["c"]) if pending else 0
        total_n = int(total_users["c"]) if total_users else 0
        paid_n = int(paid_users["c"]) if paid_users else 0
        stats["total_users"] = total_n
        stats["paid_users"] = paid_n
        stats["conversion_pct"] = round((paid_n / total_n) * 100, 1) if total_n else 0.0
        return stats


def daily_report_stats() -> dict[str, Any]:
    return today_stats()


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
