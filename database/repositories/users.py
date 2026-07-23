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
    # Yangi user uchun referral; mavjud userda referred_by_id bo'sh bo'lsa keyinroq attach_referrer
    ref_for_insert = referred_by_id if (not existed and referred_by_id) else None
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
            VALUES (?, ?, ?, ?, ?, 0, ?, datetime('now'), datetime('now'), datetime('now'))
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
            (tid, username, first_name, last_name, full_name, ref_for_insert),
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


def attach_referrer_if_empty(telegram_id: int, referrer_id: int) -> bool:
    """Mavjud userda referred_by_id bo'sh bo'lsa bir marta biriktirish."""
    tid = int(telegram_id)
    rid = int(referrer_id)
    if tid == rid or rid <= 0:
        return False
    with get_connection() as conn:
        row = conn.execute(
            "SELECT referred_by_id FROM users WHERE telegram_id = ?",
            (tid,),
        ).fetchone()
        if not row:
            return False
        if row["referred_by_id"]:
            return False
        cur = conn.execute(
            """
            UPDATE users
            SET referred_by_id = ?, updated_at = datetime('now')
            WHERE telegram_id = ? AND referred_by_id IS NULL
            """,
            (rid, tid),
        )
        return cur.rowcount > 0


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
    """1 do'st to'lagan = 1 mukofot."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE referred_by_id = ? AND referred_paid = 1",
            (int(referrer_id),),
        ).fetchone()
    return int(row["c"]) if row else 0


def get_referral_progress(referrer_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        rows = _referred_active_rows(conn, int(referrer_id))
        paid_row = conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE referred_by_id = ? AND referred_paid = 1",
            (int(referrer_id),),
        ).fetchone()
        rewarded_row = conn.execute(
            "SELECT referrals_rewarded_batches FROM users WHERE telegram_id = ?",
            (int(referrer_id),),
        ).fetchone()
    active_count = len(rows)
    paid_count = int(paid_row["c"]) if paid_row else 0
    rewarded = int(rewarded_row["referrals_rewarded_batches"] or 0) if rewarded_row else 0
    pending = max(0, paid_count - rewarded)
    return {
        "active_count": active_count,
        "paid_count": paid_count,
        "batch_progress": 1 if pending else 0,
        "batch_has_paid": paid_count > 0,
        "rewards_pending": pending,
    }


def _evaluate_referrer_reward(conn, referrer_id: int) -> dict[str, Any]:
    """Har bir to'lov qilgan do'st uchun +1 kredit."""
    rid = int(referrer_id)
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM users WHERE referred_by_id = ? AND referred_paid = 1",
        (rid,),
    ).fetchone()
    eligible = int(row["c"]) if row else 0

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

    active_row = conn.execute(
        "SELECT COUNT(*) AS c FROM users WHERE referred_by_id = ? AND referred_active = 1",
        (rid,),
    ).fetchone()
    paid_count = eligible
    rewarded_batches_after = eligible if rewarded else rewarded_batches
    pending = max(0, paid_count - rewarded_batches_after)
    return {
        "referrer_id": rid,
        "active_count": int(active_row["c"]) if active_row else 0,
        "paid_count": paid_count,
        "batch_progress": 1 if pending else 0,
        "batch_has_paid": paid_count > 0,
        "rewarded": rewarded,
        "credits_added": new_rewards,
    }


def mark_referral_paid(telegram_id: int) -> dict[str, Any] | None:
    """Taklif qilingan foydalanuvchi pullik xarid qilganda → referrerga +1."""
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


def ensure_pay_promo(telegram_id: int) -> dict[str, Any]:
    """24 soatlik 'bugun to'lasangiz +1 cover' oynasini yoqadi/yangilaydi."""
    from config.settings import settings

    tid = int(telegram_id)
    hours = max(1, int(getattr(settings, "pay_promo_hours", 24) or 24))
    with get_connection() as conn:
        row = conn.execute(
            "SELECT pay_promo_expires_at FROM users WHERE telegram_id = ?",
            (tid,),
        ).fetchone()
        if not row:
            return {"active": False, "expires_at": None, "hours_left": 0}

        expires = row["pay_promo_expires_at"]
        still_active = False
        if expires:
            ok = conn.execute(
                "SELECT 1 AS ok WHERE datetime(?) > datetime('now')",
                (str(expires),),
            ).fetchone()
            still_active = bool(ok)

        if not still_active:
            conn.execute(
                """
                UPDATE users
                SET pay_promo_expires_at = datetime('now', ?),
                    updated_at = datetime('now')
                WHERE telegram_id = ?
                """,
                (f"+{hours} hours", tid),
            )
            expires_row = conn.execute(
                "SELECT pay_promo_expires_at FROM users WHERE telegram_id = ?",
                (tid,),
            ).fetchone()
            expires = expires_row["pay_promo_expires_at"] if expires_row else None

        hours_left = 0
        if expires:
            hl = conn.execute(
                """
                SELECT CAST((julianday(?) - julianday('now')) * 24 AS INTEGER) AS h
                """,
                (str(expires),),
            ).fetchone()
            hours_left = max(0, int(hl["h"] or 0)) if hl else 0

    return {"active": True, "expires_at": expires, "hours_left": hours_left}


def activate_referral(telegram_id: int) -> dict[str, Any] | None:
    """
    Do'st birinchi hujjatni yuklaganda faol bo'ladi.
    Mukofot faqat do'st to'lov qilganda (+1).
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
        # Nested get_connection() ochmaslik — progress shu conn da
        active_row = conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE referred_by_id = ? AND referred_active = 1",
            (referrer_id,),
        ).fetchone()
        paid_row = conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE referred_by_id = ? AND referred_paid = 1",
            (referrer_id,),
        ).fetchone()
        return {
            "referrer_id": referrer_id,
            "rewarded": False,
            "credits_added": 0,
            "active_count": int(active_row["c"]) if active_row else 0,
            "paid_count": int(paid_row["c"]) if paid_row else 0,
            "batch_progress": 0,
            "batch_has_paid": False,
        }
