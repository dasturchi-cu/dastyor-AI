"""GZip — PDF/binary API yo'llarini siqmaydi (Telegram WebView mosligi)."""

from __future__ import annotations

from starlette.middleware.gzip import GZipMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

_NO_GZIP_PREFIXES = (
    "/api/preview_obyektivka",
    "/api/test_obyektivka_pdf",
    "/api/export_obyektivka",
    "/api/export_cv",
    "/api/cv_preview",
)


class SelectiveGZipMiddleware(GZipMiddleware):
    def __init__(self, app: ASGIApp, minimum_size: int = 512) -> None:
        super().__init__(app, minimum_size=minimum_size)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            path = scope.get("path") or ""
            if any(path.startswith(prefix) for prefix in _NO_GZIP_PREFIXES):
                await self.app(scope, receive, send)
                return
        await super().__call__(scope, receive, send)
