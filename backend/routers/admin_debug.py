"""Admin debug endpoints — SQLite inspection."""
from __future__ import annotations

import os

from fastapi import APIRouter, Header, HTTPException, Query, Request

from config.settings import settings
from config.validate import is_production
from database.inspect import get_database_info
from shared.auth import is_admin, resolve_uid

router = APIRouter(tags=["admin-debug"])


def _admin_authorized(
    request: Request,
    telegram_id: str | None,
    token: str | None,
    x_admin_secret: str | None,
    authorization: str | None,
) -> bool:
    uid = resolve_uid(telegram_id, token)
    if is_admin(uid):
        return True

    secret = (x_admin_secret or "").strip()
    if authorization and authorization.lower().startswith("bearer "):
        secret = secret or authorization[7:].strip()
    if not secret:
        return False

    allowed: set[str] = set()
    debug_secret = os.getenv("ADMIN_DEBUG_SECRET", "").strip()
    if debug_secret:
        allowed.add(debug_secret)
    if not is_production() and settings.webhook_secret:
        allowed.add(settings.webhook_secret)
    return secret in allowed


@router.get("/admin/db-info")
async def admin_db_info(
    request: Request,
    telegram_id: str | None = Query(None, description="Admin Telegram ID"),
    token: str | None = Query(None, description="Session token"),
    x_admin_secret: str | None = Header(None, alias="X-Admin-Secret"),
    authorization: str | None = Header(None),
):
    """
    SQLite inspection: tables, row counts, indexes, file size.
    Auth: admin telegram_id+token, or header X-Admin-Secret / Bearer WEBHOOK_SECRET.
    Compatible with DB Browser for SQLite — open `db_path` from response.
    """
    if not _admin_authorized(request, telegram_id, token, x_admin_secret, authorization):
        raise HTTPException(status_code=403, detail="Admin access required")

    return get_database_info()


@router.post("/admin/payments/reset")
async def admin_reset_payments(
    request: Request,
    telegram_id: str | None = Query(None),
    token: str | None = Query(None),
    x_admin_secret: str | None = Header(None, alias="X-Admin-Secret"),
    authorization: str | None = Header(None),
):
    """
    Barcha to'lovlarni o'chirib, ID sequence ni 0 ga qaytaradi.
    Keyingi to'lov #1 dan boshlanadi.
    DIQQAT: Bu amalni qaytarib bo'lmaydi!
    """
    if not _admin_authorized(request, telegram_id, token, x_admin_secret, authorization):
        raise HTTPException(status_code=403, detail="Admin access required")

    from database.connection import get_connection

    with get_connection() as conn:
        count_before = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
        conn.execute("DELETE FROM payments")
        conn.execute("DELETE FROM sqlite_sequence WHERE name = 'payments'")
        count_after = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]

    return {
        "ok": True,
        "deleted": count_before,
        "remaining": count_after,
        "message": f"{count_before} ta to'lov o'chirildi. Keyingi to'lov #1 dan boshlanadi.",
    }


@router.get("/admin/recent-errors")
async def admin_recent_errors(
    request: Request,
    limit: int = 10,
    telegram_id: str | None = Query(None),
    token: str | None = Query(None),
    x_admin_secret: str | None = Header(None, alias="X-Admin-Secret"),
    authorization: str | None = Header(None),
):
    if not _admin_authorized(request, telegram_id, token, x_admin_secret, authorization):
        raise HTTPException(status_code=403, detail="Admin access required")

    from database.connection import get_connection

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM error_logs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return {"ok": True, "errors": [dict(r) for r in rows]}

