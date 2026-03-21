"""WebApp static path logging + HTML 404 fallback (Telegram WebView)."""
from __future__ import annotations

import logging
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from starlette.responses import Response

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
                try:
                    return FileResponse("webapp/index.html")
                except Exception:
                    return response
        return response
