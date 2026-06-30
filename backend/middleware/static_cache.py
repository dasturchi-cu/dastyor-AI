"""Static fayllar uchun Cache-Control headerlar middleware.

/webapp/*.js, /webapp/*.css -> max-age=86400 (1 kun)
/webapp/*.html              -> max-age=300 (5 daqiqa) + must-revalidate
/health                     -> no-cache
"""
from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send


class StaticCacheMiddleware:
    """Static fayllarga mos Cache-Control header qo'shadi."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path") or ""
        cache_header = _cache_header_for(path)

        async def send_with_cache(message):
            if message["type"] == "http.response.start" and cache_header:
                headers = list(message.get("headers", []))
                existing = [h for h in headers if h[0].lower() == b"cache-control"]
                if not existing:
                    headers.append((b"cache-control", cache_header.encode()))
                    message = dict(message, headers=headers)
            await send(message)

        await self.app(scope, receive, send_with_cache)


def _cache_header_for(path: str) -> str | None:
    if path.startswith("/api/") or path.startswith("/tg/") or path.startswith("/webhook"):
        return None
    if path in ("/health", "/status"):
        return "no-cache"
    if path.endswith(".js") or path.endswith(".css"):
        return "public, max-age=86400, stale-while-revalidate=3600"
    if any(path.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp", ".ico", ".woff", ".woff2", ".ttf")):
        return "public, max-age=604800, immutable"
    if path.endswith(".html") or path in ("/", "/webapp/", "/webapp/cv", "/webapp/obyektivka"):
        return "public, max-age=300, must-revalidate"
    return None


def register_static_cache_middleware(app) -> None:
    app.add_middleware(StaticCacheMiddleware)
