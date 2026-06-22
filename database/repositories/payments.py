"""Payment repository."""
from __future__ import annotations

from typing import Any

from database.connection import get_connection, row_to_dict
from database.repositories import users as users_repo
from database.repositories import admin_data


def create_payment(
    telegram_id: int,
    payer_name: str,
    card_number: str = "",
    receipt_path: str | None = None,
    *,
    document_type: str | None = None,
) -> dict[str, Any] | None:
    user = users_repo.upsert_user(telegram_id)
    uid = int(user["id"])
    doc = (document_type or "").strip().lower()[:32] or None
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO payments (user_id, payer_name, card_number, receipt_path, document_type, status)
            VALUES (?, ?, ?, ?, ?, 'PENDING')
            """,
            (uid, payer_name.strip()[:120], card_number.strip()[:32], receipt_path, doc),
        )
        pid = cur.lastrowid
        row = conn.execute("SELECT * FROM payments WHERE id = ?", (pid,)).fetchone()
    payment = row_to_dict(row)
    if payment:
        from shared.activity import log_payment

        user = users_repo.get_by_id(uid)
        tid = int(user["telegram_id"]) if user else 0
        name = payer_name.strip()[:80] or "Foydalanuvchi"
        log_payment(tid, name, document=doc or "")
        admin_data.invalidate_metrics_cache()
    return payment


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
        ok = cur.rowcount > 0
    if ok:
        admin_data.invalidate_metrics_cache()
    return ok


def approve_atomic(payment_id: int, admin_note: str | None = None) -> dict[str, Any] | None:
    """
    Atomically: PENDING → APPROVED + grant 1 credit.
    Idempotent if already APPROVED (no extra credit).
    """
    pid = int(payment_id)
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT p.id, p.status, p.user_id, u.telegram_id
            FROM payments p
            JOIN users u ON u.id = p.user_id
            WHERE p.id = ?
            """,
            (pid,),
        ).fetchone()
        if not row:
            return None

        status = str(row["status"] or "").upper()
        if status == "APPROVED":
            pass
        elif status == "PENDING":
            cur = conn.execute(
                """
                UPDATE payments
                SET status = 'APPROVED',
                    admin_note = COALESCE(?, admin_note),
                    updated_at = datetime('now')
                WHERE id = ? AND status = 'PENDING'
                """,
                (admin_note, pid),
            )
            if cur.rowcount != 1:
                return None
            conn.execute(
                """
                UPDATE users
                SET credits = credits + 1, updated_at = datetime('now')
                WHERE id = ?
                """,
                (int(row["user_id"]),),
            )
            users_repo.invalidate_cache(int(row["telegram_id"]))
        else:
            return None

    admin_data.invalidate_metrics_cache()
    return get_payment(pid)


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


def count_user_payments(user_id: int) -> int:
    """Total payment submissions for a user (purchase counter)."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM payments WHERE user_id = ?",
            (int(user_id),),
        ).fetchone()
    return int(row["c"]) if row else 0


def count_user_approved_payments(user_id: int, *, exclude_payment_id: int | None = None) -> int:
    with get_connection() as conn:
        if exclude_payment_id:
            row = conn.execute(
                """
                SELECT COUNT(*) AS c FROM payments
                WHERE user_id = ? AND status = 'APPROVED' AND id != ?
                """,
                (int(user_id), int(exclude_payment_id)),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT COUNT(*) AS c FROM payments
                WHERE user_id = ? AND status = 'APPROVED'
                """,
                (int(user_id),),
            ).fetchone()
    return int(row["c"]) if row else 0


def list_stale_pending(hours: int = 12, limit: int = 20) -> list[dict[str, Any]]:
    hours = max(1, int(hours))
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT p.*, u.telegram_id, u.first_name, u.last_name, u.username
            FROM payments p
            JOIN users u ON u.id = p.user_id
            WHERE p.status = 'PENDING'
              AND p.pending_reminder_sent_at IS NULL
              AND p.created_at <= datetime('now', ?)
            ORDER BY p.created_at ASC
            LIMIT ?
            """,
            (f"-{hours} hours", limit),
        ).fetchall()
    return [row_to_dict(r) for r in rows if r]


def mark_pending_reminder_sent(payment_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            """
            UPDATE payments
            SET pending_reminder_sent_at = datetime('now'),
                updated_at = datetime('now')
            WHERE id = ? AND status = 'PENDING'
            """,
            (int(payment_id),),
        )
        return cur.rowcount > 0


def set_document_type(payment_id: int, document_type: str) -> bool:
    doc = (document_type or "").strip().lower()[:32]
    if not doc:
        return False
    with get_connection() as conn:
        cur = conn.execute(
            """
            UPDATE payments SET document_type = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (doc, int(payment_id)),
        )
        return cur.rowcount > 0


def list_filtered(
    *,
    period: str | None = None,
    status: str | None = None,
    limit: int = 50,
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
        SELECT p.*, u.telegram_id, u.first_name, u.last_name, u.username
        FROM payments p JOIN users u ON u.id = p.user_id
        {where}
        ORDER BY p.created_at DESC LIMIT ?
    """
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [row_to_dict(r) for r in rows if r]
