"""Security dashboard API — admin only."""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query, Request

from backend.routers.admin_debug import _admin_authorized
from database.repositories import security_dashboard as sec_dash_repo
from shared.security_audit import EVENT_ADMIN_ACCESS, log_security_event

router = APIRouter(tags=["security"])


@router.get("/admin/security")
async def admin_security_dashboard(
    request: Request,
    telegram_id: str | None = Query(None),
    token: str | None = Query(None),
    x_admin_secret: str | None = Header(None, alias="X-Admin-Secret"),
    authorization: str | None = Header(None),
):
    if not _admin_authorized(request, telegram_id, token, x_admin_secret, authorization):
        raise HTTPException(status_code=403, detail="Admin access required")

    from core.security import client_ip

    log_security_event(
        EVENT_ADMIN_ACCESS,
        ip=client_ip(request),
        user_id=int(telegram_id) if telegram_id and telegram_id.isdigit() else None,
        details="security_dashboard",
    )
    snapshot = sec_dash_repo.security_snapshot()
    return {"ok": True, **snapshot}
