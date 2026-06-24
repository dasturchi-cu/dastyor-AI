"""Test/audit ma'lumotlarini bazadan tozalash — faqat real statistika qolsin."""
from __future__ import annotations

import logging

from database.connection import get_connection, row_to_dict
from shared.payment_test_filter import is_test_payment, is_test_user

logger = logging.getLogger(__name__)


def purge_test_payments() -> int:
    """Test to'lovlari va yetim (user yo'q) yozuvlarni o'chirish."""
    deleted = 0
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT p.id, p.payer_name, u.telegram_id, u.username, u.first_name, u.last_name
            FROM payments p
            LEFT JOIN users u ON u.id = p.user_id
            """
        ).fetchall()
        for row in rows:
            item = row_to_dict(row) or {}
            if is_test_payment(item) or item.get("telegram_id") is None:
                conn.execute("DELETE FROM payments WHERE id = ?", (int(item["id"]),))
                deleted += 1
    return deleted


def purge_orphan_documents() -> int:
    """User o'chirilgandan qolgan CV/Obyektivka yozuvlari."""
    removed = 0
    with get_connection() as conn:
        removed += conn.execute(
            "DELETE FROM cv_documents WHERE user_id NOT IN (SELECT id FROM users)"
        ).rowcount
        removed += conn.execute(
            "DELETE FROM obyektivka_documents WHERE user_id NOT IN (SELECT id FROM users)"
        ).rowcount
        removed += conn.execute(
            "DELETE FROM documents WHERE user_id NOT IN (SELECT id FROM users)"
        ).rowcount
    return removed


def purge_test_activity_events() -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """
            DELETE FROM activity_events
            WHERE lower(COALESCE(actor_name, '')) LIKE '%audit%'
               OR lower(COALESCE(actor_name, '')) LIKE '%smoke%'
               OR lower(COALESCE(detail, '')) LIKE '%audit%'
               OR lower(COALESCE(detail, '')) LIKE '%smoke%'
            """
        )
        return int(cur.rowcount or 0)


def reset_payment_id_sequence() -> bool:
    """To'lovlar bo'sh bo'lsa keyingi to'lov #1 dan boshlanadi."""
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
        if int(count or 0) != 0:
            return False
        conn.execute("DELETE FROM sqlite_sequence WHERE name = 'payments'")
    return True


def purge_all_test_data() -> dict[str, int]:
    """Startup: test userlar, to'lovlar, hujjatlar, faollik — tozalash."""
    from database.repositories.users import purge_test_users
    from shared.error_log import purge_noise_error_logs

    removed_users = purge_test_users()
    removed_payments = purge_test_payments()
    removed_docs = purge_orphan_documents()
    removed_activity = purge_test_activity_events()
    removed_errors = purge_noise_error_logs()
    sequence_reset = reset_payment_id_sequence()

    summary = {
        "users": len(removed_users),
        "payments": removed_payments,
        "documents": removed_docs,
        "activity": removed_activity,
        "errors": removed_errors,
        "payment_sequence_reset": int(sequence_reset),
    }
    if any(summary.values()):
        logger.info("Test data purge: %s", summary)
    return summary
