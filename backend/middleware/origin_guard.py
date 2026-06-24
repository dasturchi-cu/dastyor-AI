"""Origin / Referer guard for state-changing API requests (CSRF mitigation)."""
from __future__ import annotations

import logging
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from config.settings import settings
from shared.security_audit import EVENT_ORIGIN_REJECTED, log_security_event

logger = logging.getLogger(__name__)

_SKIP_PATHS = frozenset({"/webhook", "/", "/health", "/api/webhook"})


def _allowed_origins() -> set[str]:
    origins: set[str] = set()
    for raw in (settings.site_base_url, settings.webapp_base):
        url = (raw or "").strip().rstrip("/")
        if url.startswith("http"):
            origins.add(url)
            parsed = urlparse(url)
            if parsed.scheme and parsed.netloc:
                origins.add(f"{parsed.scheme}://{parsed.netloc}")
    if settings.allow_insecure_auth:
        origins.update(
            {
                "http://127.0.0.1:8000",
                "http://localhost:8000",
                "http://127.0.0.1",
                "http://localhost",
            }
        )
    origins.add("https://web.telegram.org")
    origins.add("https://telegram.org")
    return origins


def _origin_allowed(origin: str, allowed: set[str]) -> bool:
    origin = origin.rstrip("/")
    if origin in allowed:
        return True
    for base in allowed:
        if origin.startswith(base):
            return True
    return False


def register_origin_guard_middleware(app) -> None:
    if settings.enforce_origin_check:
        app.add_middleware(OriginGuardMiddleware)


class OriginGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return await call_next(request)
        if not path.startswith("/api/"):
            return await call_next(request)
        if path in _SKIP_PATHS:
            return await call_next(request)

        allowed = _allowed_origins()
        origin = (request.headers.get("Origin") or "").strip()
        referer = (request.headers.get("Referer") or "").strip()

        if origin and _origin_allowed(origin, allowed):
            return await call_next(request)
        if referer:
            ref_origin = referer.split("/", 3)
            if len(ref_origin) >= 3:
                ref_base = f"{ref_origin[0]}//{ref_origin[2]}"
                if _origin_allowed(ref_base.rstrip("/"), allowed):
                    return await call_next(request)

        if not origin and not referer:
            return await call_next(request)

        from core.security import client_ip

        ip = client_ip(request)
        log_security_event(
            EVENT_ORIGIN_REJECTED,
            severity="warn",
            ip=ip,
            details=f"path={path} origin={origin[:80]}",
        )
        return JSONResponse(
            status_code=403,
            content={"detail": "Origin not allowed"},
        )
