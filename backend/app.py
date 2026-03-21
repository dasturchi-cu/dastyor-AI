"""
ASGI application: WebApp static files, REST API, Telegram webhook, Celery job routes.

Root cause addressed: `docker-compose` used `backend.app:app`, which only exposed
`/api/ocr` (async Celery) and `/api/jobs/*`, while the Telegram WebApp lived in
`api_webhook.py` — so a containerized deploy never served `/webapp/*` or `/api/auth`.

Use either:
  uvicorn backend.app:app
  uvicorn api_webhook:app
Both resolve to the same application object.
"""

from api_webhook import app

__all__ = ["app"]
