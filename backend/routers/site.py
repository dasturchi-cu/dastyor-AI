"""Health checks and WebApp entry (Telegram WebView: avoid redirect-only root)."""
from __future__ import annotations

import time

from fastapi import APIRouter
from fastapi.responses import FileResponse, RedirectResponse, Response

from backend.paths import webapp_index_path
from core.redis_client import ping_async, redis_enabled
from database.verify import check_db_integrity, verify_schema

router = APIRouter(tags=["site"])


_NO_CACHE_HTML = {
    "Cache-Control": "no-store, no-cache, must-revalidate",
    "Pragma": "no-cache",
}


def _index_response():
    """Serve index.html directly — some Telegram WebViews handle redirects poorly."""
    p = webapp_index_path()
    if p.is_file():
        return FileResponse(
            str(p),
            media_type="text/html; charset=utf-8",
            headers=_NO_CACHE_HTML,
        )
    return RedirectResponse(url="/webapp/index.html")


@router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


@router.get("/health")
async def health():
    redis_status = "disabled"
    if redis_enabled():
        redis_status = "ok" if await ping_async() else "unavailable"
    db_ok, db_msg = check_db_integrity()
    schema = verify_schema() if db_ok else {"ok": False}
    return {
        "ok": db_ok and schema.get("ok", False),
        "status": "healthy" if db_ok and schema.get("ok") else "degraded",
        "webapp_mounted": True,
        "redis": redis_status,
        "database": db_msg,
        "schema": schema.get("tables") if schema else None,
        "time": time.time(),
    }


@router.get("/webapp")
async def webapp_root():
    return _index_response()


@router.get("/webapp/")
async def webapp_root_trailing_slash():
    return _index_response()


@router.get("/webapp/index.html")
async def webapp_index_explicit():
    """BotFather: .../webapp/index.html — ba'zi CDN/proksi faqat shu yo'lni chaqiradi."""
    return _index_response()


@router.get("/")
async def root():
    return _index_response()


@router.get("/index.html")
async def root_index_alias():
    """BotFather sometimes uses https://host/index.html without /webapp prefix."""
    return _index_response()


@router.get("/app")
async def app_menu_alias():
    """Common typo / short path for menu button URL."""
    return _index_response()
