"""
Production ASGI app: Telegram webhook + static WebApp + REST API + optional Celery job routes.

Root causes addressed:
- api_webhook.py monolith (2k+ LOC) split into routers/services.
- Duplicate /health and mixed concerns separated.
- PaddleOCR logic unified with Celery worker (backend.services.paddle_ocr_runtime).
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.paths import webapp_dir, webapp_index_path
from backend.exception_handlers import register_exception_handlers
from backend.middleware.webapp import register_webapp_middleware
from backend.routers.documents_web import router as documents_router
from backend.routers.jobs import router as jobs_router
from backend.routers.ocr import router as ocr_jobs_router
from backend.routers.ocr_web import router as ocr_web_router
from backend.routers.public_web import router as public_router
from backend.routers.site import router as site_router
from backend.routers.telegram_files_web import router as telegram_files_router
from backend.routers.tg_update import router as tg_update_router

logger = logging.getLogger(__name__)

try:
    load_dotenv()
except Exception:
    pass


def create_webhook_app() -> FastAPI:
    from main import setup_application

    application = setup_application()
    if application is None:
        raise RuntimeError("BOT_TOKEN is missing — cannot start webhook application")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.ptb_application = application
        await application.initialize()
        await application.start()

        webhook_url = os.getenv(
            "WEBHOOK_URL",
            "https://dastyor-ai-production.up.railway.app/webhook",
        ).strip()
        logger.info("Setting webhook to: %s", webhook_url)
        await application.bot.set_webhook(url=webhook_url, drop_pending_updates=True)
        logger.info("Webhook application started")
        yield
        await application.stop()
        await application.shutdown()
        logger.info("Webhook application stopped")

    app = FastAPI(
        lifespan=lifespan,
        title="Dastyor AI — Webhook + Web API",
        version="2.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_webapp_middleware(app)
    register_exception_handlers(app)

    # Order: specific routes before static mount
    app.include_router(site_router)
    app.include_router(public_router)
    app.include_router(ocr_web_router)
    app.include_router(documents_router)
    app.include_router(telegram_files_router)
    app.include_router(jobs_router)
    app.include_router(ocr_jobs_router)
    app.include_router(tg_update_router)

    _wd = webapp_dir()
    _ix = webapp_index_path()
    if not _ix.is_file():
        logger.error(
            "WebApp index missing at %s (cwd=%s). Set WORKDIR to project root in Docker.",
            _ix,
            __import__("os").getcwd(),
        )
    else:
        logger.info("WebApp static dir=%s index_ok=True", _wd)

    app.mount("/webapp", StaticFiles(directory=str(_wd), html=True), name="webapp")
    return app
