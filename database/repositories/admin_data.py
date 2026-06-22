"""Admin panel — barcha SQLite so'rovlari (yagona manba)."""
from __future__ import annotations

import logging
from typing import Any

from config.settings import settings
from database.connection import get_connection, row_to_dict
from shared import cache as ttl_cache

logger = logging.getLogger(__name__)

_CACHE_KEY = "admin:metrics"
_CACHE_TTL = 3.0


def invalidate_metrics_cache() -> None:
    ttl_cache.invalidate(_CACHE_KEY)
    ttl_cache.invalidate("admin:dashboard")


def _scalar(conn, sql: str, params: tuple = ()) -> int:
    row = conn.execute(sql, params).fetchone()
    return int(row[0]) if row else 0


def get_global_metrics() -> dict[str, Any]:
    """Barcha asosiy hisob-kitoblar — faqat SQLite."""
    hit = ttl_cache.get(_CACHE_KEY)
    if hit is not None:
        return hit

    online_m = max(1, settings.online_user_minutes)
    inactive_d = max(1, settings.inactive_user_days)
    price = settings.single_doc_price_uzs

    with get_connection() as conn:
        users_count = _scalar(conn, "SELECT COUNT(*) FROM users")
        pending = _scalar(conn, "SELECT COUNT(*) FROM payments WHERE status = 'PENDING'")
        approved = _scalar(conn, "SELECT COUNT(*) FROM payments WHERE status = 'APPROVED'")
        rejected = _scalar(conn, "SELECT COUNT(*) FROM payments WHERE status = 'REJECTED'")
        payments_total = _scalar(conn, "SELECT COUNT(*) FROM payments")
        cv_total = _scalar(conn, "SELECT COUNT(*) FROM generated_files WHERE file_type = 'cv'")
        oby_total = _scalar(
            conn, "SELECT COUNT(*) FROM generated_files WHERE file_type = 'obyektivka'"
        )
        docs_total = cv_total + oby_total
        paid_users = _scalar(
            conn,
            "SELECT COUNT(DISTINCT user_id) FROM payments WHERE status = 'APPROVED'",
        )
        active_today = _scalar(
            conn,
            """
            SELECT COUNT(*) FROM users
            WHERE date(COALESCE(last_active_at, updated_at)) = date('now')
            """,
        )
        online_now = _scalar(
            conn,
            f"""
            SELECT COUNT(*) FROM users
            WHERE datetime(COALESCE(last_active_at, updated_at))
                  >= datetime('now', '-{online_m} minutes')
            """,
        )
        inactive = _scalar(
            conn,
            f"""
            SELECT COUNT(*) FROM users
            WHERE datetime(COALESCE(last_active_at, updated_at))
                  < datetime('now', '-{inactive_d} days')
            """,
        )
        new_users_today = _scalar(
            conn, "SELECT COUNT(*) FROM users WHERE date(created_at) = date('now')"
        )
        approved_today = _scalar(
            conn,
            """
            SELECT COUNT(*) FROM payments
            WHERE status = 'APPROVED' AND date(created_at) = date('now')
            """,
        )
        cv_today = _scalar(
            conn,
            """
            SELECT COUNT(*) FROM generated_files
            WHERE file_type = 'cv' AND date(created_at) = date('now')
            """,
        )
        oby_today = _scalar(
            conn,
            """
            SELECT COUNT(*) FROM generated_files
            WHERE file_type = 'obyektivka' AND date(created_at) = date('now')
            """,
        )

        feed_rows = conn.execute(
            """
            SELECT event_type, actor_name, detail, created_at
            FROM activity_events
            ORDER BY id DESC LIMIT 8
            """
        ).fetchall()

        top_purchase = conn.execute(
            """
            SELECT u.telegram_id, u.username, u.first_name, u.last_name,
                   SUM(CASE WHEN p.status = 'APPROVED' THEN 1 ELSE 0 END) AS approved_count
            FROM users u
            JOIN payments p ON p.user_id = u.id
            GROUP BY u.id
            HAVING approved_count > 0
            ORDER BY approved_count DESC
            LIMIT 3
            """
        ).fetchall()

    revenue_total = approved * price
    revenue_today = approved_today * price
    conversion = round((paid_users / users_count) * 100, 1) if users_count else 0.0

    data: dict[str, Any] = {
        "users_count": users_count,
        "pending_payments": pending,
        "approved_payments": approved,
        "rejected_payments": rejected,
        "payments_total": payments_total,
        "cv_total": cv_total,
        "obyektivka_total": oby_total,
        "documents_total": docs_total,
        "revenue_uzs": revenue_total,
        "revenue_today_uzs": revenue_today,
        "paid_users": paid_users,
        "active_users": active_today,
        "online_users": online_now,
        "inactive_users": inactive,
        "new_users_today": new_users_today,
        "cv_today": cv_today,
        "obyektivka_today": oby_today,
        "approved_today": approved_today,
        "conversion_pct": conversion,
        "feed": [row_to_dict(r) for r in feed_rows if r],
        "top_users": [row_to_dict(r) for r in top_purchase if r],
        "single_doc_price_uzs": price,
    }
    ttl_cache.set(_CACHE_KEY, data, _CACHE_TTL)
    logger.debug(
        "admin metrics: users=%s pending=%s approved=%s cv=%s oby=%s",
        users_count,
        pending,
        approved,
        cv_total,
        oby_total,
    )
    return data


def list_users_enriched(limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT u.id, u.telegram_id, u.username, u.first_name, u.last_name,
                   u.credits, u.is_blocked, u.created_at,
                   COALESCE(u.last_active_at, u.updated_at) AS last_activity,
                   (SELECT COUNT(*) FROM payments p WHERE p.user_id = u.id) AS payments_count,
                   (SELECT COUNT(*) FROM generated_files g
                    WHERE g.user_id = u.id AND g.file_type = 'cv') AS cv_count,
                   (SELECT COUNT(*) FROM generated_files g
                    WHERE g.user_id = u.id AND g.file_type = 'obyektivka') AS obyektivka_count
            FROM users u
            ORDER BY u.created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
    return [row_to_dict(r) for r in rows if r]


def search_users_enriched(query: str, limit: int = 10) -> list[dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return []
    base_sql = """
        SELECT u.id, u.telegram_id, u.username, u.first_name, u.last_name,
               u.credits, u.created_at,
               COALESCE(u.last_active_at, u.updated_at) AS last_activity,
               (SELECT COUNT(*) FROM payments p WHERE p.user_id = u.id) AS payments_count,
               (SELECT COUNT(*) FROM generated_files g
                WHERE g.user_id = u.id AND g.file_type = 'cv') AS cv_count,
               (SELECT COUNT(*) FROM generated_files g
                WHERE g.user_id = u.id AND g.file_type = 'obyektivka') AS obyektivka_count
        FROM users u
        WHERE {where}
        ORDER BY u.created_at DESC
        LIMIT ?
    """
    with get_connection() as conn:
        if q.isdigit():
            rows = conn.execute(
                base_sql.format(where="CAST(u.telegram_id AS TEXT) LIKE ?"),
                (f"%{q}%", limit),
            ).fetchall()
        else:
            term = q.lstrip("@").strip()
            like = f"%{term}%"
            rows = conn.execute(
                base_sql.format(
                    where="""
                    u.username LIKE ? COLLATE NOCASE
                    OR u.first_name LIKE ? COLLATE NOCASE
                    OR u.last_name LIKE ? COLLATE NOCASE
                    OR (u.first_name || ' ' || COALESCE(u.last_name, '')) LIKE ? COLLATE NOCASE
                    OR u.payer_name LIKE ? COLLATE NOCASE
                    """
                ),
                (like, like, like, like, like, limit),
            ).fetchall()
    return [row_to_dict(r) for r in rows if r]


def list_payments_enriched(
    *,
    period: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    period_key = (period or "").lower()
    if period_key == "today":
        clauses.append("date(p.created_at) = date('now')")
    elif period_key == "week":
        clauses.append("p.created_at >= datetime('now', '-7 days')")
    elif period_key == "month":
        clauses.append("p.created_at >= datetime('now', '-30 days')")
    if status:
        clauses.append("p.status = ?")
        params.append(status.upper())
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    sql = f"""
        SELECT p.id, p.user_id, p.payer_name, p.document_type, p.status,
               p.created_at, p.receipt_path,
               u.telegram_id, u.username, u.first_name, u.last_name
        FROM payments p
        JOIN users u ON u.id = p.user_id
        {where}
        ORDER BY p.created_at DESC
        LIMIT ?
    """
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    price = settings.single_doc_price_uzs
    result = []
    for r in rows:
        d = row_to_dict(r) or {}
        d["amount_uzs"] = price
        result.append(d)
    return result


def top_users_report(limit: int = 5) -> dict[str, list[dict[str, Any]]]:
    with get_connection() as conn:
        by_purchases = conn.execute(
            """
            SELECT u.telegram_id, u.username, u.first_name, u.last_name,
                   COUNT(p.id) AS total_payments,
                   SUM(CASE WHEN p.status = 'APPROVED' THEN 1 ELSE 0 END) AS approved_count
            FROM users u
            JOIN payments p ON p.user_id = u.id
            GROUP BY u.id
            ORDER BY approved_count DESC, total_payments DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        by_documents = conn.execute(
            """
            SELECT u.telegram_id, u.username, u.first_name, u.last_name,
                   SUM(CASE WHEN g.file_type = 'cv' THEN 1 ELSE 0 END) AS cv_count,
                   SUM(CASE WHEN g.file_type = 'obyektivka' THEN 1 ELSE 0 END) AS oby_count,
                   COUNT(g.id) AS docs_total
            FROM users u
            JOIN generated_files g ON g.user_id = u.id
            GROUP BY u.id
            ORDER BY docs_total DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        by_activity = conn.execute(
            """
            SELECT u.telegram_id, u.username, u.first_name, u.last_name,
                   COALESCE(u.last_active_at, u.updated_at) AS last_activity,
                   (SELECT COUNT(*) FROM payments p WHERE p.user_id = u.id) AS payments_count,
                   (SELECT COUNT(*) FROM generated_files g WHERE g.user_id = u.id) AS docs_count
            FROM users u
            ORDER BY datetime(COALESCE(u.last_active_at, u.updated_at)) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return {
        "by_purchases": [row_to_dict(r) for r in by_purchases if r],
        "by_documents": [row_to_dict(r) for r in by_documents if r],
        "by_activity": [row_to_dict(r) for r in by_activity if r],
    }


def count_users() -> int:
    with get_connection() as conn:
        return _scalar(conn, "SELECT COUNT(*) FROM users")


def export_statistics_rows() -> list[dict[str, Any]]:
    price = settings.single_doc_price_uzs
    periods = [
        ("bugun", "date(created_at) = date('now')"),
        ("hafta", "created_at >= datetime('now', '-7 days')"),
        ("oy", "created_at >= datetime('now', '-30 days')"),
        ("jami", "1=1"),
    ]
    rows: list[dict[str, Any]] = []
    with get_connection() as conn:
        for label, cond in periods:
            users = _scalar(conn, f"SELECT COUNT(*) FROM users WHERE {cond}")
            payments = _scalar(conn, f"SELECT COUNT(*) FROM payments WHERE {cond}")
            approved = _scalar(
                conn, f"SELECT COUNT(*) FROM payments WHERE status='APPROVED' AND {cond}"
            )
            rejected = _scalar(
                conn, f"SELECT COUNT(*) FROM payments WHERE status='REJECTED' AND {cond}"
            )
            pending = _scalar(
                conn, f"SELECT COUNT(*) FROM payments WHERE status='PENDING' AND {cond}"
            )
            cv = _scalar(
                conn,
                f"SELECT COUNT(*) FROM generated_files WHERE file_type='cv' AND {cond}",
            )
            oby = _scalar(
                conn,
                f"SELECT COUNT(*) FROM generated_files WHERE file_type='obyektivka' AND {cond}",
            )
            rows.append(
                {
                    "period": label,
                    "users": users,
                    "payments": payments,
                    "approved": approved,
                    "rejected": rejected,
                    "pending": pending,
                    "cv": cv,
                    "obyektivka": oby,
                    "revenue_uzs": approved * price,
                }
            )
    return rows
