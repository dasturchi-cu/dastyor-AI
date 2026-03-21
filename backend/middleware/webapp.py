"""WebApp static path logging + HTML 404 fallback (Telegram WebView)."""
from __future__ import annotations

import logging
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse

from backend.paths import webapp_index_path

logger = logging.getLogger("dastyor.webapp")


def _spa_entry_fallback_path(path: str) -> bool:
    """
    Telegram WebView ba'zan Accept: */* va UA da 'telegram' bo'lmasin.
    Shunday 404 larda ham bosh sahifani berish kerak.
    """
    p = (path or "").split("?", 1)[0].rstrip("/") or "/"
    if p == "/":
        return True
    if p in ("/webapp", "/app", "/index.html"):
        return True
    if not p.startswith("/webapp"):
        return False
    rest = p[len("/webapp") :].lstrip("/")
    if not rest:
        return True
    if "/" in rest:
        return False
    ext = rest.rsplit(".", 1)[-1].lower() if "." in rest else ""
    return ext in ("", "html", "htm")


def register_webapp_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def log_webapp_gets(request: Request, call_next: Callable):
        if request.method == "GET" and request.url.path.startswith("/webapp"):
            response = await call_next(request)
            try:
                logger.info(
                    "Webapp GET path=%s status=%s",
                    request.url.path,
                    getattr(response, "status_code", None),
                )
            except Exception:
                pass
            return response
        return await call_next(request)

    @app.middleware("http")
    async def webapp_404_fallback_to_index(request: Request, call_next: Callable):
        response = await call_next(request)
        if (
            request.method == "GET"
            and response.status_code == 404
            and request.url.path.startswith("/webapp")
        ):
            accept = (request.headers.get("accept") or "").lower()
            p = request.url.path
            if (
                "text/html" in accept
                or "*/*" in accept
                or p.endswith(".html")
                or p.endswith("/")
                or p.rstrip("/").endswith("/webapp")
            ):
                idx = webapp_index_path()
                if idx.is_file():
                    try:
                        return FileResponse(str(idx), media_type="text/html; charset=utf-8")
                    except Exception:
                        return response
        return response

    @app.middleware("http")
    async def telegram_unknown_path_to_webapp(request: Request, call_next: Callable):
        """
        Menu / noto'g'ri URL → 404 bo'lsa, Telegram WebView uchun index.html (Accept */* ham).
        """
        response = await call_next(request)
        if response.status_code != 404 or request.method != "GET":
            return response
        path = request.url.path
        if (
            path.startswith("/api")
            or path.startswith("/webhook")
            or path.startswith("/docs")
            or path.startswith("/redoc")
            or path.startswith("/openapi")
        ):
            return response
        if not _spa_entry_fallback_path(path):
            return response
        idx = webapp_index_path()
        if not idx.is_file():
            return response
        try:
            return FileResponse(str(idx), media_type="text/html; charset=utf-8")
        except Exception:
            return response
