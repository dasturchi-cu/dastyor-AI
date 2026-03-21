"""Health checks and WebApp entry (Telegram WebView: avoid redirect-only root)."""
from __future__ import annotations

import time

from fastapi import APIRouter
from fastapi.responses import FileResponse, RedirectResponse

from backend.paths import webapp_index_path

router = APIRouter(tags=["site"])


def _index_response():
    """Serve index.html directly — some Telegram WebViews handle redirects poorly."""
    p = webapp_index_path()
    if p.is_file():
        return FileResponse(str(p), media_type="text/html; charset=utf-8")
    return RedirectResponse(url="/webapp/index.html")


@router.get("/health")
async def health():
    return {
        "ok": True,
        "status": "healthy",
        "webapp_mounted": True,
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
