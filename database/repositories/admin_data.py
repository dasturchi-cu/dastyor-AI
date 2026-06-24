"""Admin panel — barcha SQLite so'rovlari (yagona manba)."""
from __future__ import annotations

import logging
from typing import Any

from config.settings import settings
from database.connection import get_connection, row_to_dict

logger = logging.getLogger(__name__)


def invalidate_metrics_cache() -> None:
    """Backward-compatible no-op (admin metrics cache removed — SQLite only)."""
    return None


def _scalar(conn, sql: str, params: tuple = ()) -> int:
    row = conn.execute(sql, params).fetchone()
    return int(row[0]) if row else 0


def _real_user_sql(alias: str = "u") -> tuple[str, tuple]:
    from shared.payment_test_filter import test_telegram_id_list

    ids = test_telegram_id_list()
    if not ids:
        return "1=1", ()
    placeholders = ",".join("?" * len(ids))
    return f"{alias}.telegram_id NOT IN ({placeholders})", tuple(ids)


def get_global_metrics() -> dict[str, Any]:
    """Barcha asosiy hisob-kitoblar — faqat real foydalanuvchilar."""
    online_m = max(1, settings.online_user_minutes)
    inactive_d = max(1, settings.inactive_user_days)
    price = settings.single_doc_price_uzs
    user_clause, user_params = _real_user_sql("u")
    pay_clause = f"p.user_id IN (SELECT id FROM users u WHERE {user_clause})"
    doc_clause = f"user_id IN (SELECT id FROM users u WHERE {user_clause})"

    with get_connection() as conn:
        users_count = _scalar(
            conn,
            f"SELECT COUNT(*) FROM users u WHERE {user_clause}",
            user_params,
        )
        pending = _scalar(
            conn,
            f"SELECT COUNT(*) FROM payments p WHERE {pay_clause} AND p.status = 'PENDING'",
            user_params,
        )
        approved = _scalar(
            conn,
            f"SELECT COUNT(*) FROM payments p WHERE {pay_clause} AND p.status = 'APPROVED'",
            user_params,
        )
        rejected = _scalar(
            conn,
            f"SELECT COUNT(*) FROM payments p WHERE {pay_clause} AND p.status = 'REJECTED'",
            user_params,
        )
        payments_total = _scalar(
            conn,
            f"SELECT COUNT(*) FROM payments p WHERE {pay_clause}",
            user_params,
        )
        cv_total = _scalar(
            conn,
            f"SELECT COUNT(*) FROM generated_files WHERE file_type = 'cv' AND {doc_clause}",
            user_params,
        )
        oby_total = _scalar(
            conn,
            f"SELECT COUNT(*) FROM generated_files WHERE file_type = 'obyektivka' AND {doc_clause}",
            user_params,
        )
        docs_total = cv_total + oby_total
        paid_users = _scalar(
            conn,
            f"""
            SELECT COUNT(DISTINCT p.user_id) FROM payments p
            JOIN users u ON u.id = p.user_id
            WHERE p.status = 'APPROVED' AND {user_clause}
            """,
            user_params,
        )
        active_today = _scalar(
            conn,
            f"""
            SELECT COUNT(*) FROM users u
            WHERE {user_clause}
              AND date(COALESCE(u.last_active_at, u.updated_at)) = date('now')
            """,
            user_params,
        )
        online_now = _scalar(
            conn,
            f"""
            SELECT COUNT(*) FROM users u
            WHERE {user_clause}
              AND datetime(COALESCE(u.last_active_at, u.updated_at))
                  >= datetime('now', '-{online_m} minutes')
            """,
            user_params,
        )
        inactive = _scalar(
            conn,
            f"""
            SELECT COUNT(*) FROM users u
            WHERE {user_clause}
              AND datetime(COALESCE(u.last_active_at, u.updated_at))
                  < datetime('now', '-{inactive_d} days')
            """,
            user_params,
        )
        new_users_today = _scalar(
            conn,
            f"""
            SELECT COUNT(*) FROM users u
            WHERE {user_clause} AND date(u.created_at) = date('now')
            """,
            user_params,
        )
        approved_today = _scalar(
            conn,
            f"""
            SELECT COUNT(*) FROM payments p
            WHERE {pay_clause} AND p.status = 'APPROVED'
              AND date(p.created_at) = date('now')
            """,
            user_params,
        )
        cv_today = _scalar(
            conn,
            f"""
            SELECT COUNT(*) FROM generated_files
            WHERE file_type = 'cv' AND {doc_clause}
              AND date(created_at) = date('now')
            """,
            user_params,
        )
        oby_today = _scalar(
            conn,
            f"""
            SELECT COUNT(*) FROM generated_files
            WHERE file_type = 'obyektivka' AND {doc_clause}
              AND date(created_at) = date('now')
            """,
            user_params,
        )
        revenue_total = _scalar(
            conn,
            f"""
            SELECT COALESCE(SUM(p.amount), 0) FROM payments p
            WHERE {pay_clause} AND p.status = 'APPROVED'
            """,
            user_params,
        )
        revenue_today = _scalar(
            conn,
            f"""
            SELECT COALESCE(SUM(p.amount), 0) FROM payments p
            WHERE {pay_clause} AND p.status = 'APPROVED'
              AND date(p.created_at) = date('now')
            """,
            user_params,
        )

        feed_rows = conn.execute(
            """
            SELECT event_type, actor_name, detail, created_at
            FROM activity_events
            ORDER BY id DESC LIMIT 8
            """
        ).fetchall()

        top_purchase = conn.execute(
            f"""
            SELECT u.telegram_id, u.username, u.first_name, u.last_name,
                   SUM(CASE WHEN p.status = 'APPROVED' THEN 1 ELSE 0 END) AS approved_count
            FROM users u
            JOIN payments p ON p.user_id = u.id
            WHERE {user_clause}
            GROUP BY u.id
            HAVING approved_count > 0
            ORDER BY approved_count DESC
            LIMIT 3
            """,
            user_params,
        ).fetchall()

    revenue_total = revenue_total or (approved * price)
    revenue_today = revenue_today or (approved_today * price)
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
    from shared.payment_test_filter import filter_real_users

    fetch = max(limit + offset, limit) * 4
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
            LIMIT ?
            """,
            (fetch,),
        ).fetchall()
    real = filter_real_users([row_to_dict(r) for r in rows if r])
    return real[offset : offset + limit]


def search_users_enriched(query: str, limit: int = 10) -> list[dict[str, Any]]:
    from shared.payment_test_filter import filter_real_users

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
                    OR EXISTS (
                        SELECT 1 FROM payments p2
                        WHERE p2.user_id = u.id AND p2.payer_name LIKE ? COLLATE NOCASE
                    )
                    """
                ),
                (like, like, like, like, like, limit),
            ).fetchall()
    return filter_real_users([row_to_dict(r) for r in rows if r])


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
    params.append(max(limit * 5, 40))
    sql = f"""
        SELECT p.id, p.user_id, p.payer_name, p.document_type, p.status,
               p.created_at, COALESCE(p.screenshot_path, p.receipt_path) AS receipt_path,
               p.payment_number, p.amount,
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
    from shared.payment_test_filter import filter_real_payments

    result = []
    for r in rows:
        d = row_to_dict(r) or {}
        d["amount_uzs"] = int(d.get("amount") or price)
        result.append(d)
    return filter_real_payments(result)[:limit]


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


def count_real_users() -> int:
    from shared.payment_test_filter import is_test_user

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT telegram_id, username, first_name, last_name FROM users"
        ).fetchall()
    return sum(1 for r in rows if r and not is_test_user(row_to_dict(r)))


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
