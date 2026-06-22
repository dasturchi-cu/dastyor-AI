"""
ASGI entrypoint: Telegram webhook + WebApp + REST API.
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

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
