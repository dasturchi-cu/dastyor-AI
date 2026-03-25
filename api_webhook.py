"""
ASGI entrypoint for Railway / Render / Docker: Telegram webhook + WebApp + REST API.

Implementation lives in backend.server_app (layered routers, shared services).
"""
from __future__ import annotations

import logging
import os

from backend.server_app import create_webhook_app

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

app = create_webhook_app()

# Sentry verify endpoint (works regardless of router ordering)
try:
    from fastapi.responses import PlainTextResponse

    @app.get("/sentry-debug", include_in_schema=False)
    @app.get("/sentry-debug/", include_in_schema=False)
    async def sentry_debug():
        if not (os.getenv("SENTRY_DSN") or "").strip():
            return PlainTextResponse("SENTRY_DSN is not set", status_code=404)
        1 / 0  # intentional (Sentry verify)

except Exception:
    pass

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
