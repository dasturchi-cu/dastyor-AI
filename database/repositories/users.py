"""User repository — SQLite is the single source of truth."""
from __future__ import annotations

import sqlite3
from typing import Any

from database.connection import get_connection, row_to_dict


def invalidate_cache(telegram_id: int) -> None:
    """Backward-compatible no-op (in-memory user cache removed)."""
    del telegram_id


def _exists_in_db(telegram_id: int) -> bool:
    tid = int(telegram_id)
    with get_connection() as conn:
        row = conn.execute("SELECT 1 FROM users WHERE telegram_id = ?", (tid,)).fetchone()
    return row is not None


def upsert_user(
    telegram_id: int,
    *,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    referred_by_id: int | None = None,
) -> dict[str, Any]:
    tid = int(telegram_id)
    existed = _exists_in_db(tid)
    if existed:
        referred_by_id = None
    full_name = " ".join(filter(None, [first_name, last_name])).strip() or None
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (
                telegram_id, username, first_name, last_name, full_name,
                credits, referred_by_id,
                first_seen_at, last_seen_at, last_active_at
            )
            VALUES (?, ?, ?, ?, ?, 1, ?, datetime('now'), datetime('now'), datetime('now'))
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = COALESCE(excluded.username, users.username),
                first_name = COALESCE(excluded.first_name, users.first_name),
                last_name = COALESCE(excluded.last_name, users.last_name),
                full_name = COALESCE(
                    excluded.full_name,
                    TRIM(COALESCE(excluded.first_name, users.first_name, '') || ' '
                         || COALESCE(excluded.last_name, users.last_name, '')),
                    users.full_name
                ),
                last_seen_at = datetime('now'),
                last_active_at = datetime('now'),
                updated_at = datetime('now')
            """,
            (tid, username, first_name, last_name, full_name, referred_by_id),
        )
        row = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (tid,)).fetchone()
    data = row_to_dict(row) or {}
    if not existed and data:
        from shared.activity import log_register

        name = " ".join(filter(None, [first_name, last_name])).strip() or "Foydalanuvchi"
        log_register(tid, name)
    return data


def get_by_telegram_id(telegram_id: int) -> dict[str, Any] | None:
    tid = int(telegram_id)
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (tid,)).fetchone()
    return row_to_dict(row)


def get_by_id(user_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (int(user_id),)).fetchone()
    return row_to_dict(row)


def list_users(limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return [row_to_dict(r) for r in rows if r]


def count_users() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
    return int(row["c"]) if row else 0


def get_credits(telegram_id: int) -> int:
    user = get_by_telegram_id(telegram_id)
    return int(user.get("credits") or 0) if user else 0


def add_credits(telegram_id: int, amount: int = 1) -> int:
    tid = int(telegram_id)
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE users SET credits = credits + ?, updated_at = datetime('now')
            WHERE telegram_id = ?
            """,
            (max(0, int(amount)), tid),
        )
        row = conn.execute("SELECT credits FROM users WHERE telegram_id = ?", (tid,)).fetchone()
    return int(row["credits"]) if row else 0


def consume_credit(telegram_id: int) -> bool:
    tid = int(telegram_id)
    with get_connection() as conn:
        cur = conn.execute(
            """
            UPDATE users SET credits = credits - 1, updated_at = datetime('now')
            WHERE telegram_id = ? AND credits > 0
            """,
            (tid,),
        )
        ok = cur.rowcount > 0
    return ok


def is_blocked(telegram_id: int) -> bool:
    user = get_by_telegram_id(telegram_id)
    return bool(int(user.get("is_blocked") or 0)) if user else False


def set_blocked(telegram_id: int, blocked: bool) -> bool:
    tid = int(telegram_id)
    with get_connection() as conn:
        cur = conn.execute(
            """
            UPDATE users SET is_blocked = ?, updated_at = datetime('now')
            WHERE telegram_id = ?
            """,
            (1 if blocked else 0, tid),
        )
        ok = cur.rowcount > 0
    return ok


def remove_credits(telegram_id: int, amount: int = 1) -> int:
    tid = int(telegram_id)
    amount = max(0, int(amount))
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE users
            SET credits = CASE WHEN credits >= ? THEN credits - ? ELSE 0 END,
                updated_at = datetime('now')
            WHERE telegram_id = ?
            """,
            (amount, amount, tid),
        )
        row = conn.execute("SELECT credits FROM users WHERE telegram_id = ?", (tid,)).fetchone()
    return int(row["credits"]) if row else 0


def search_users(query: str, limit: int = 10) -> list[dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return []
    with get_connection() as conn:
        if q.isdigit():
            rows = conn.execute(
                """
                SELECT * FROM users
                WHERE CAST(telegram_id AS TEXT) LIKE ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (f"%{q}%", limit),
            ).fetchall()
        else:
            term = q.lstrip("@").strip()
            like = f"%{term}%"
            rows = conn.execute(
                """
                SELECT * FROM users
                WHERE username LIKE ? COLLATE NOCASE
                   OR first_name LIKE ? COLLATE NOCASE
                   OR last_name LIKE ? COLLATE NOCASE
                   OR (first_name || ' ' || COALESCE(last_name, '')) LIKE ? COLLATE NOCASE
                ORDER BY created_at DESC LIMIT ?
                """,
                (like, like, like, like, limit),
            ).fetchall()
    return [row_to_dict(r) for r in rows if r]


def list_broadcast_targets() -> list[int]:
    from shared.payment_test_filter import is_test_user

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT telegram_id, username, first_name, last_name
            FROM users WHERE is_blocked = 0 ORDER BY id
            """
        ).fetchall()
    out: list[int] = []
    for row in rows:
        user = row_to_dict(row)
        if user and not is_test_user(user):
            out.append(int(user["telegram_id"]))
    return out


def purge_test_users() -> list[int]:
    """Test/audit foydalanuvchilarni va ularning ma'lumotlarini o'chirish (CASCADE)."""
    from config.settings import settings
    from shared.payment_test_filter import is_test_user

    protect: set[int] = set(settings.admin_user_ids or ())

    deleted: list[int] = []
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, telegram_id, username, first_name, last_name FROM users"
        ).fetchall()
        for row in rows:
            user = row_to_dict(row) or {}
            tid = int(user.get("telegram_id") or 0)
            if tid in protect or not is_test_user(user):
                continue
            conn.execute("DELETE FROM users WHERE id = ?", (int(user["id"]),))
            deleted.append(tid)

    if deleted:
        try:
            from database.repositories.admin_data import invalidate_metrics_cache

            invalidate_metrics_cache()
        except Exception:
            pass
    return deleted


def get_profile_stats(telegram_id: int) -> dict[str, Any] | None:
    user = get_by_telegram_id(telegram_id)
    if not user:
        return None
    uid = int(user["id"])
    with get_connection() as conn:
        cv_row = conn.execute(
            "SELECT COUNT(*) AS c FROM generated_files WHERE user_id = ? AND file_type = 'cv'",
            (uid,),
        ).fetchone()
        oby_row = conn.execute(
            """
            SELECT COUNT(*) AS c FROM generated_files
            WHERE user_id = ? AND file_type = 'obyektivka'
            """,
            (uid,),
        ).fetchone()
        pay_row = conn.execute(
            "SELECT COUNT(*) AS c FROM payments WHERE user_id = ?",
            (uid,),
        ).fetchone()
    return {
        **user,
        "cv_count": int(cv_row["c"]) if cv_row else 0,
        "obyektivka_count": int(oby_row["c"]) if oby_row else 0,
        "payments_count": int(pay_row["c"]) if pay_row else 0,
        "last_activity": user.get("last_active_at") or user.get("updated_at"),
    }


def get_referral_count(telegram_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE referred_by_id = ? AND referred_active = 1",
            (int(telegram_id),),
        ).fetchone()
    return int(row["c"]) if row else 0


def _referred_active_rows(conn, referrer_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT referred_active, referred_paid
        FROM users
        WHERE referred_by_id = ? AND referred_active = 1
        ORDER BY COALESCE(referred_active_at, updated_at) ASC, telegram_id ASC
        """,
        (int(referrer_id),),
    ).fetchall()


def count_eligible_referral_batches(referrer_id: int) -> int:
    with get_connection() as conn:
        rows = _referred_active_rows(conn, int(referrer_id))
    eligible = 0
    for index in range(0, len(rows), 3):
        chunk = rows[index : index + 3]
        if len(chunk) < 3:
            break
        if any(int(r["referred_paid"] or 0) for r in chunk):
            eligible += 1
    return eligible


def get_referral_progress(referrer_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        rows = _referred_active_rows(conn, int(referrer_id))
        paid_row = conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE referred_by_id = ? AND referred_paid = 1",
            (int(referrer_id),),
        ).fetchone()
    active_count = len(rows)
    paid_count = int(paid_row["c"]) if paid_row else 0
    batch_progress = active_count % 3
    if batch_progress == 0 and active_count > 0:
        current_chunk = rows[-3:]
        batch_progress = 3
    elif batch_progress == 0:
        current_chunk = []
    else:
        current_chunk = rows[-batch_progress:]
    batch_has_paid = any(int(r["referred_paid"] or 0) for r in current_chunk)
    return {
        "active_count": active_count,
        "paid_count": paid_count,
        "batch_progress": batch_progress,
        "batch_has_paid": batch_has_paid,
    }


def _evaluate_referrer_reward(conn, referrer_id: int) -> dict[str, Any]:
    rid = int(referrer_id)
    eligible = 0
    rows = _referred_active_rows(conn, rid)
    for index in range(0, len(rows), 3):
        chunk = rows[index : index + 3]
        if len(chunk) < 3:
            break
        if any(int(r["referred_paid"] or 0) for r in chunk):
            eligible += 1

    ref_user = conn.execute(
        "SELECT referrals_rewarded_batches FROM users WHERE telegram_id = ?",
        (rid,),
    ).fetchone()
    rewarded_batches = int(ref_user["referrals_rewarded_batches"] or 0) if ref_user else 0
    new_rewards = max(0, eligible - rewarded_batches)
    rewarded = new_rewards > 0
    if rewarded:
        conn.execute(
            """
            UPDATE users
            SET credits = credits + ?,
                referrals_rewarded_batches = ?,
                updated_at = datetime('now')
            WHERE telegram_id = ?
            """,
            (new_rewards, eligible, rid),
        )
        invalidate_cache(rid)

    progress = get_referral_progress(rid)
    return {
        "referrer_id": rid,
        "active_count": progress["active_count"],
        "paid_count": progress["paid_count"],
        "batch_progress": progress["batch_progress"],
        "batch_has_paid": progress["batch_has_paid"],
        "rewarded": rewarded,
        "credits_added": new_rewards,
    }


def mark_referral_paid(telegram_id: int) -> dict[str, Any] | None:
    """Taklif qilingan foydalanuvchi pullik xarid qilganda."""
    tid = int(telegram_id)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT referred_by_id, referred_paid FROM users WHERE telegram_id = ?",
            (tid,),
        ).fetchone()
        if not row or not row["referred_by_id"]:
            return None
        if int(row["referred_paid"] or 0) != 1:
            conn.execute(
                """
                UPDATE users
                SET referred_paid = 1, updated_at = datetime('now')
                WHERE telegram_id = ?
                """,
                (tid,),
            )
            invalidate_cache(tid)
        return _evaluate_referrer_reward(conn, int(row["referred_by_id"]))


def activate_referral(telegram_id: int) -> dict[str, Any] | None:
    """
    Taklif qilingan do'st birinchi hujjatini yuklab olganda faollashtiriladi.
    Mukofot: har 3 ta faol taklif guruhi + guruhdan kamida 1 pullik xarid.
    """
    tid = int(telegram_id)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT referred_by_id, referred_active FROM users WHERE telegram_id = ?",
            (tid,),
        ).fetchone()
        if not row or not row["referred_by_id"] or int(row["referred_active"] or 0) == 1:
            return None

        referrer_id = int(row["referred_by_id"])
        conn.execute(
            """
            UPDATE users
            SET referred_active = 1,
                referred_active_at = COALESCE(referred_active_at, datetime('now')),
                updated_at = datetime('now')
            WHERE telegram_id = ?
            """,
            (tid,),
        )
        invalidate_cache(tid)
        return _evaluate_referrer_reward(conn, referrer_id)
