"""
Request ID middleware.

Adds a stable correlation id for logs/debugging:
- Accepts incoming X-Request-Id (if present and sane)
- Otherwise generates a new uuid4 hex
- Exposes it via request.state.request_id and response header X-Request-Id
"""
from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Request
from starlette.responses import Response


def _sanitize_request_id(value: str | None) -> str | None:
    if not value:
        return None
    v = str(value).strip()
    if not v:
        return None
    # Avoid log/header abuse
    if len(v) > 80:
        return None
    return v


def register_request_id_middleware(app) -> None:
    @app.middleware("http")
    async def request_id_mw(request: Request, call_next: Callable) -> Response:
        rid = _sanitize_request_id(request.headers.get("x-request-id")) or uuid.uuid4().hex
        request.state.request_id = rid
        response = await call_next(request)
        try:
            response.headers["X-Request-Id"] = rid
        except Exception:
            pass
        return response

