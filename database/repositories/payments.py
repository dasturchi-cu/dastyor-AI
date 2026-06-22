"""Payment repository."""
from __future__ import annotations

from typing import Any

from database.connection import get_connection, row_to_dict
from database.repositories import users as users_repo


def create_payment(
    telegram_id: int,
    payer_name: str,
    card_number: str = "",
    receipt_path: str | None = None,
) -> dict[str, Any] | None:
    user = users_repo.upsert_user(telegram_id)
    uid = int(user["id"])
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO payments (user_id, payer_name, card_number, receipt_path, status)
            VALUES (?, ?, ?, ?, 'PENDING')
            """,
            (uid, payer_name.strip()[:120], card_number.strip()[:32], receipt_path),
        )
        pid = cur.lastrowid
        row = conn.execute("SELECT * FROM payments WHERE id = ?", (pid,)).fetchone()
    return row_to_dict(row)


def update_receipt(payment_id: int, receipt_path: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            """
            UPDATE payments SET receipt_path = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (receipt_path, int(payment_id)),
        )
        return cur.rowcount > 0


def get_payment(payment_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT p.*, u.telegram_id, u.first_name, u.username
            FROM payments p
            JOIN users u ON u.id = p.user_id
            WHERE p.id = ?
            """,
            (int(payment_id),),
        ).fetchone()
    return row_to_dict(row)


def get_user_payment(payment_id: int, telegram_id: int) -> dict[str, Any] | None:
    payment = get_payment(payment_id)
    if not payment or int(payment.get("telegram_id") or 0) != int(telegram_id):
        return None
    return payment


def set_status(payment_id: int, status: str, admin_note: str | None = None) -> bool:
    status = status.upper()
    if status not in ("PENDING", "APPROVED", "REJECTED"):
        return False
    with get_connection() as conn:
        cur = conn.execute(
            """
            UPDATE payments SET status = ?, admin_note = COALESCE(?, admin_note),
            updated_at = datetime('now')
            WHERE id = ?
            """,
            (status, admin_note, int(payment_id)),
        )
        return cur.rowcount > 0


def list_payments(status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if status:
            rows = conn.execute(
                """
                SELECT p.*, u.telegram_id, u.first_name, u.username
                FROM payments p JOIN users u ON u.id = p.user_id
                WHERE p.status = ?
                ORDER BY p.created_at DESC LIMIT ?
                """,
                (status.upper(), limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT p.*, u.telegram_id, u.first_name, u.username
                FROM payments p JOIN users u ON u.id = p.user_id
                ORDER BY p.created_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [row_to_dict(r) for r in rows if r]


def count_pending() -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM payments WHERE status = 'PENDING'"
        ).fetchone()
    return int(row["c"]) if row else 0


def count_user_pending(telegram_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS c FROM payments p
            JOIN users u ON u.id = p.user_id
            WHERE u.telegram_id = ? AND p.status = 'PENDING'
            """,
            (int(telegram_id),),
        ).fetchone()
    return int(row["c"]) if row else 0
