"""
Request timing + slow-path logging. Adds X-Process-Time-ms for debugging.
"""
from __future__ import annotations

import logging
import os
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("perf.request")

_SLOW_MS = float(os.getenv("PERF_SLOW_REQUEST_MS", "800") or "800")
_LOG_ALL = os.getenv("PERF_LOG_ALL", "").strip().lower() in ("1", "true", "yes")


class PerformanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        t0 = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        try:
            response.headers["X-Process-Time-ms"] = f"{elapsed_ms:.2f}"
        except Exception:
            pass
        path = request.url.path
        if _LOG_ALL:
            logger.info("%s %s %.1fms", request.method, path, elapsed_ms)
        elif elapsed_ms >= _SLOW_MS and not path.startswith("/webapp/"):
            logger.warning("SLOW %s %s %.1fms", request.method, path, elapsed_ms)
        return response
