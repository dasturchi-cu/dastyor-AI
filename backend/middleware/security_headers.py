"""HTTP security headers middleware."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from config.validate import is_production


def register_security_headers_middleware(app) -> None:
    app.add_middleware(SecurityHeadersMiddleware)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        path = request.url.path
        is_webapp = path.startswith("/webapp") or path in ("/", "/index.html", "/favicon.ico")

        response.headers.setdefault("X-Content-Type-Options", "nosniff")

        if is_webapp:
            # Telegram WebApp needs to be embeddable in Telegram iframe / webview.
            if "X-Frame-Options" in response.headers:
                del response.headers["X-Frame-Options"]
        else:
            response.headers.setdefault("X-Frame-Options", "DENY")

        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=()",
        )
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        if is_production():
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://telegram.org https://challenges.cloudflare.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https: wss:; "
            "frame-src https://telegram.org https://challenges.cloudflare.com; "
            "frame-ancestors 'self' https://web.telegram.org https://*.telegram.org https://telegram.org https://t.me https://*.t.me; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers.setdefault("Content-Security-Policy", csp)
        return response
