"""AI monitoring API — live dashboard data."""
from __future__ import annotations

import os

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse

from backend.routers.admin_debug import _admin_authorized
from config.settings import WEBAPP_DIR, settings
from database.repositories.ai_routing import snapshot_to_dict
from features.ai.routing.config import load_routing_config

router = APIRouter(tags=["ai-monitoring"])


@router.get("/admin/ai-monitor/status")
async def ai_monitor_status(
    request: Request,
    telegram_id: str | None = Query(None),
    token: str | None = Query(None),
    x_admin_secret: str | None = Header(None, alias="X-Admin-Secret"),
    authorization: str | None = Header(None),
):
    if not _admin_authorized(request, telegram_id, token, x_admin_secret, authorization):
        raise HTTPException(status_code=403, detail="Admin access required")
    return snapshot_to_dict()


@router.get("/admin/ai-monitor/quota-history")
async def ai_monitor_quota_history(
    request: Request,
    telegram_id: str | None = Query(None),
    token: str | None = Query(None),
    provider: str | None = Query(None),
    key_index: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    x_admin_secret: str | None = Header(None, alias="X-Admin-Secret"),
    authorization: str | None = Header(None),
):
    if not _admin_authorized(request, telegram_id, token, x_admin_secret, authorization):
        raise HTTPException(status_code=403, detail="Admin access required")
    from database.repositories.ai_quota import list_history

    return {"history": list_history(provider=provider, key_index=key_index, limit=limit)}


@router.get("/admin/ai-monitor/config")
async def ai_monitor_config(
    request: Request,
    telegram_id: str | None = Query(None),
    token: str | None = Query(None),
    x_admin_secret: str | None = Header(None, alias="X-Admin-Secret"),
    authorization: str | None = Header(None),
):
    if not _admin_authorized(request, telegram_id, token, x_admin_secret, authorization):
        raise HTTPException(status_code=403, detail="Admin access required")

    cfg = load_routing_config()
    providers_summary = {}
    for pname, pcfg in cfg.providers.items():
        providers_summary[pname.value] = {
            "key_count": len(pcfg.api_keys),
            "models": list(pcfg.models),
            "configured": bool(pcfg.api_keys),
        }
    return {
        "primary_provider": cfg.primary_provider.value,
        "fallback_order": [p.value for p in cfg.fallback_order],
        "request_timeout_ms": cfg.request_timeout_ms,
        "max_retries": cfg.max_retries,
        "cooldown_ms": cfg.cooldown_ms,
        "providers": providers_summary,
    }


@router.get("/admin/ai-monitor")
async def ai_monitor_page(
    request: Request,
    telegram_id: str | None = Query(None),
    token: str | None = Query(None),
    x_admin_secret: str | None = Header(None, alias="X-Admin-Secret"),
    authorization: str | None = Header(None),
):
    """Serve monitoring dashboard (admin auth via query params or headers)."""
    if not _admin_authorized(request, telegram_id, token, x_admin_secret, authorization):
        raise HTTPException(status_code=403, detail="Admin access required")

    path = WEBAPP_DIR / "ai-monitor.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="ai-monitor.html not found")
    return FileResponse(path, media_type="text/html")
