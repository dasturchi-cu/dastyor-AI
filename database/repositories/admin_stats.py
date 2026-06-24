"""Admin stats — backward-compatible API over admin_data (SQLite only)."""
from __future__ import annotations

from typing import Any

from config.settings import settings
from database.connection import get_connection, row_to_dict
from database.repositories import admin_data

invalidate_metrics_cache = admin_data.invalidate_metrics_cache


def dashboard_snapshot() -> dict[str, Any]:
    from shared.payment_test_filter import filter_real_users

    data = admin_data.get_global_metrics()
    data["users_count"] = admin_data.count_real_users()
    data["top_users"] = filter_real_users(data.get("top_users") or [])
    return data


def today_stats() -> dict[str, Any]:
    m = admin_data.get_global_metrics()
    return {
        "new_users": m.get("new_users_today", 0),
        "payments": m.get("approved_today", 0) + m.get("pending_payments", 0),
        "approved_payments": m.get("approved_today", 0),
        "cv": m.get("cv_today", 0),
        "obyektivka": m.get("obyektivka_today", 0),
        "revenue_uzs": m.get("revenue_today_uzs", 0),
        "active_users": m.get("active_users", 0),
        "pending_payments": m.get("pending_payments", 0),
        "total_users": m.get("users_count", 0),
        "paid_users": m.get("paid_users", 0),
        "conversion_pct": m.get("conversion_pct", 0.0),
    }


def daily_report_stats() -> dict[str, Any]:
    return today_stats()


def top_payers(limit: int = 10) -> list[dict[str, Any]]:
    report = admin_data.top_users_report(limit)
    return report.get("by_purchases") or []


def export_users_rows() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT u.telegram_id, u.username, u.first_name, u.last_name,
                   u.credits, u.is_blocked, u.created_at,
                   COALESCE(u.last_active_at, u.updated_at) AS last_activity,
                   (SELECT COUNT(*) FROM payments p WHERE p.user_id = u.id) AS payments_count,
                   (SELECT COUNT(*) FROM generated_files g
                    WHERE g.user_id = u.id AND g.file_type = 'cv') AS cv_count,
                   (SELECT COUNT(*) FROM generated_files g
                    WHERE g.user_id = u.id AND g.file_type = 'obyektivka') AS obyektivka_count
            FROM users u
            ORDER BY u.created_at DESC
            """
        ).fetchall()
    return [row_to_dict(r) for r in rows if r]


def export_payments_rows() -> list[dict[str, Any]]:
    price = settings.single_doc_price_uzs
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT p.id, u.telegram_id, u.username, u.first_name, u.last_name,
                   p.payer_name, p.document_type, p.status, p.created_at
            FROM payments p
            JOIN users u ON u.id = p.user_id
            ORDER BY p.created_at DESC
            """
        ).fetchall()
    result = []
    for r in rows:
        d = row_to_dict(r) or {}
        d["amount_uzs"] = price
        result.append(d)
    return result


export_statistics_rows = admin_data.export_statistics_rows
list_users_enriched = admin_data.list_users_enriched
search_users_enriched = admin_data.search_users_enriched
list_payments_enriched = admin_data.list_payments_enriched
top_users_report = admin_data.top_users_report
count_users = admin_data.count_users
count_real_users = admin_data.count_real_users
