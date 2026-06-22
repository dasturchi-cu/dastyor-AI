"""Admin debug endpoints — SQLite inspection."""
from __future__ import annotations

import os

from fastapi import APIRouter, Header, HTTPException, Query, Request

from config.settings import settings
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

    allowed = {s for s in (settings.webhook_secret, os.getenv("ADMIN_DEBUG_SECRET", "")) if s}
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
