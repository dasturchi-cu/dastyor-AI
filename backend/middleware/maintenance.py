"""
Maintenance mode middleware for FastAPI.

Requirement: if maintenance_mode is ON -> web + api should not work (except webhook/health).
"""
from __future__ import annotations

import logging
from typing import Callable

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

logger = logging.getLogger("dastyor.maintenance")


def _is_exempt(path: str) -> bool:
    p = (path or "").lower()
    if p.startswith("/webhook"):
        return True
    if p in ("/health", "/api/health"):
        return True
    if p.startswith("/openapi") or p.startswith("/docs") or p.startswith("/redoc"):
        return True
    return False


def register_maintenance_middleware(app) -> None:
    @app.middleware("http")
    async def maintenance_gate(request: Request, call_next: Callable) -> Response:
        try:
            from database.repositories.settings import is_maintenance

            if is_maintenance() and not _is_exempt(request.url.path):
                # Block both /api and /webapp (and other pages).
                if request.url.path.lower().startswith("/api"):
                    return JSONResponse(
                        status_code=503,
                        content={"ok": False, "detail": "🛠 Texnik ishlar. Keyinroq urinib ko‘ring."},
                        headers={"Cache-Control": "no-store"},
                    )
                return HTMLResponse(
                    status_code=503,
                    content=(
                        "<!doctype html><html><head><meta charset='utf-8'/>"
                        "<meta name='viewport' content='width=device-width,initial-scale=1'/>"
                        "<title>Maintenance</title></head>"
                        "<body style='font-family:system-ui;padding:24px'>"
                        "<h2>🛠 Texnik ishlar</h2>"
                        "<p>Hozir xizmatlar vaqtincha o‘chirilgan. Iltimos, keyinroq urinib ko‘ring.</p>"
                        "</body></html>"
                    ),
                    headers={"Cache-Control": "no-store"},
                )
        except Exception as e:
            logger.debug("maintenance middleware skipped: %s", e)
        return await call_next(request)

