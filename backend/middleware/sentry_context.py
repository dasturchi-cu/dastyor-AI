"""
Attach request/user context to Sentry events.

This makes Sentry issues actionable:
- which endpoint failed
- which telegram_id (if present)
- request metadata (safe)
"""
from __future__ import annotations

import logging
from typing import Callable

from fastapi import Request
from starlette.responses import Response

logger = logging.getLogger("dastyor.sentry")


def _extract_uid(request: Request) -> int | None:
    try:
        # token-based endpoints often carry telegram_id query param
        q = request.query_params
        tid = q.get("telegram_id") or q.get("user_id")
        if tid:
            return int(str(tid))
    except Exception:
        pass
    # Some POST bodies carry telegram_id; we avoid reading body here (can be large).
    return None


def register_sentry_context_middleware(app) -> None:
    @app.middleware("http")
    async def sentry_context(request: Request, call_next: Callable) -> Response:
        try:
            import sentry_sdk

            uid = _extract_uid(request)
            with sentry_sdk.configure_scope() as scope:
                scope.set_tag("http.method", request.method)
                scope.set_tag("http.path", request.url.path)
                if uid is not None:
                    scope.set_user({"id": uid})
                # safe request context
                scope.set_context(
                    "request_meta",
                    {
                        "query": str(request.url.query)[:500],
                        "ua": (request.headers.get("user-agent") or "")[:200],
                        "host": (request.headers.get("host") or "")[:120],
                    },
                )
        except Exception:
            # Sentry not configured or import error; ignore
            pass
        return await call_next(request)

