"""WebApp static path logging + HTML 404 fallback (Telegram WebView)."""
from __future__ import annotations

import logging
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse

from backend.paths import webapp_index_path

logger = logging.getLogger("dastyor.webapp")


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
            accept = request.headers.get("accept", "")
            if "text/html" in accept or request.url.path.endswith(".html") or request.url.path.endswith("/"):
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
        Menu button URL xato bo'lsa (masalan / ilova yo'li), Telegram WebView 404 + "Not Found".
        HTML so'rov yoki Telegram User-Agent bo'lsa index.html beramiz (API yo'llarini tegmaymiz).
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
        ua = (request.headers.get("user-agent") or "").lower()
        acc = request.headers.get("accept", "")
        looks_html = "text/html" in acc or "telegram" in ua
        if not looks_html:
            return response
        last = path.rstrip("/").split("/")[-1] if path else ""
        if "." in last and not last.endswith(".html"):
            return response
        idx = webapp_index_path()
        if not idx.is_file():
            return response
        try:
            return FileResponse(str(idx), media_type="text/html; charset=utf-8")
        except Exception:
            return response
