"""User repository."""
from __future__ import annotations

from typing import Any

from database.connection import get_connection, row_to_dict
from shared import cache as ttl_cache

_USER_TTL = 20.0


def _invalidate(telegram_id: int) -> None:
    ttl_cache.invalidate(f"user:{int(telegram_id)}")


def invalidate_cache(telegram_id: int) -> None:
    _invalidate(int(telegram_id))


def upsert_user(
    telegram_id: int,
    *,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> dict[str, Any]:
    tid = int(telegram_id)
    existed = get_by_telegram_id(tid) is not None
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (telegram_id, username, first_name, last_name, last_active_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = COALESCE(excluded.username, users.username),
                first_name = COALESCE(excluded.first_name, users.first_name),
                last_name = COALESCE(excluded.last_name, users.last_name),
                last_active_at = datetime('now'),
                updated_at = datetime('now')
            """,
            (tid, username, first_name, last_name),
        )
        row = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (tid,)).fetchone()
    _invalidate(tid)
    data = row_to_dict(row) or {}
    if data:
        ttl_cache.set(f"user:{tid}", data, _USER_TTL)
    if not existed and data:
        from shared.activity import log_register

        name = " ".join(filter(None, [first_name, last_name])).strip() or "Foydalanuvchi"
        log_register(tid, name)
    return data


def get_by_telegram_id(telegram_id: int) -> dict[str, Any] | None:
    tid = int(telegram_id)
    key = f"user:{tid}"
    hit = ttl_cache.get(key)
    if hit is not None:
        return hit
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (tid,)).fetchone()
    data = row_to_dict(row)
    if data:
        ttl_cache.set(key, data, _USER_TTL)
    return data


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


def _access_column(doc_type: str) -> str:
    key = (doc_type or "").strip().lower()
    if key in ("cv",):
        return "has_cv_access"
    if key in ("obyektivka", "oby", "objective"):
        return "has_objective_access"
    raise ValueError(f"Unknown document type: {doc_type}")


def has_document_access(telegram_id: int, doc_type: str) -> bool:
    user = get_by_telegram_id(telegram_id)
    if not user:
        return False
    col = _access_column(doc_type)
    return bool(int(user.get(col) or 0))


def grant_document_access(telegram_id: int, doc_type: str) -> bool:
    tid = int(telegram_id)
    col = _access_column(doc_type)
    with get_connection() as conn:
        cur = conn.execute(
            f"""
            UPDATE users SET {col} = 1, updated_at = datetime('now')
            WHERE telegram_id = ?
            """,
            (tid,),
        )
        ok = cur.rowcount > 0
    if ok:
        _invalidate(tid)
    return ok


def revoke_document_access(telegram_id: int, doc_type: str) -> bool:
    tid = int(telegram_id)
    col = _access_column(doc_type)
    with get_connection() as conn:
        cur = conn.execute(
            f"""
            UPDATE users SET {col} = 0, updated_at = datetime('now')
            WHERE telegram_id = ?
            """,
            (tid,),
        )
        ok = cur.rowcount > 0
    if ok:
        _invalidate(tid)
    return ok


def reset_document_access(telegram_id: int) -> bool:
    tid = int(telegram_id)
    with get_connection() as conn:
        cur = conn.execute(
            """
            UPDATE users
            SET has_cv_access = 0, has_objective_access = 0, updated_at = datetime('now')
            WHERE telegram_id = ?
            """,
            (tid,),
        )
        ok = cur.rowcount > 0
    if ok:
        _invalidate(tid)
    return ok


def consume_document_access(telegram_id: int, doc_type: str) -> bool:
    tid = int(telegram_id)
    col = _access_column(doc_type)
    with get_connection() as conn:
        cur = conn.execute(
            f"""
            UPDATE users SET {col} = 0, updated_at = datetime('now')
            WHERE telegram_id = ? AND {col} = 1
            """,
            (tid,),
        )
        ok = cur.rowcount > 0
    if ok:
        _invalidate(tid)
    return ok


def access_status(telegram_id: int) -> dict[str, bool]:
    user = get_by_telegram_id(telegram_id)
    if not user:
        return {"has_cv_access": False, "has_objective_access": False}
    return {
        "has_cv_access": bool(int(user.get("has_cv_access") or 0)),
        "has_objective_access": bool(int(user.get("has_objective_access") or 0)),
    }


def grant_access_for_payment_document(document_type: str | None) -> list[str]:
    """Return document types unlocked by payment approval."""
    key = (document_type or "manual").strip().lower()
    if key == "cv":
        return ["cv"]
    if key in ("obyektivka", "oby"):
        return ["obyektivka"]
    return ["cv", "obyektivka"]


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
    if ok:
        _invalidate(tid)
    return ok


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
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT telegram_id FROM users WHERE is_blocked = 0 ORDER BY id"
        ).fetchall()
    return [int(r["telegram_id"]) for r in rows if r]


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
        pending_row = conn.execute(
            """
            SELECT id FROM payments
            WHERE user_id = ? AND status = 'PENDING'
            ORDER BY created_at DESC LIMIT 1
            """,
            (uid,),
        ).fetchone()
    return {
        **user,
        "cv_count": int(cv_row["c"]) if cv_row else 0,
        "obyektivka_count": int(oby_row["c"]) if oby_row else 0,
        "payments_count": int(pay_row["c"]) if pay_row else 0,
        "last_activity": user.get("last_active_at") or user.get("updated_at"),
        "pending_payment_id": int(pending_row["id"]) if pending_row else None,
    }
