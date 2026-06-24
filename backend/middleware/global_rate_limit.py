"""Global API rate limit middleware — baseline protection for all /api routes."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from config.settings import settings
from core.security import _check_rate_bucket, client_ip
from shared.security_audit import EVENT_RATE_LIMIT, log_security_event


def register_global_rate_limit_middleware(app) -> None:
    if settings.global_rate_limit_per_minute > 0:
        app.add_middleware(GlobalRateLimitMiddleware)


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)

        ip = client_ip(request)
        limit = settings.global_rate_limit_per_minute
        if not await _check_rate_bucket("global:all", limit):
            log_security_event(EVENT_RATE_LIMIT, severity="warn", ip=ip, details="global_middleware")
            return JSONResponse(
                status_code=429,
                content={"detail": "Juda ko'p so'rov. Biroz kuting."},
            )
        return await call_next(request)
