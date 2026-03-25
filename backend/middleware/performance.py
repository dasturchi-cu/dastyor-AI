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
        try:
            response = await call_next(request)
            ok = True
        except Exception as e:
            ok = False
            # Fire-and-forget system log for unhandled API errors
            try:
                from bot.utils.system_tracker import track_event_fire_and_forget

                track_event_fire_and_forget(
                    telegram_id=None,
                    username=None,
                    event_type="ERROR",
                    action_name=f"http:{request.method}:{request.url.path}",
                    status="failed",
                    error_message=str(e)[:2000],
                    execution_time_ms=int((time.perf_counter() - t0) * 1000),
                    metadata={"query": str(request.url.query)[:500]},
                )
            except Exception:
                pass
            raise
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
        # Optional: real-time HTTP end events (only for /api)
        try:
            if path.startswith("/api"):
                from bot.utils.system_tracker import track_event_fire_and_forget

                track_event_fire_and_forget(
                    telegram_id=None,
                    username=None,
                    event_type="HTTP",
                    action_name=f"http:{request.method}:{path}",
                    status="success" if ok and getattr(response, "status_code", 500) < 500 else "failed",
                    execution_time_ms=int(elapsed_ms),
                    metadata={"status_code": getattr(response, "status_code", None)},
                )
        except Exception:
            pass
        return response
