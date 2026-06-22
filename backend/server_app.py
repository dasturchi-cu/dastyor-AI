"""Production ASGI app: Aiogram webhook + WebApp + REST API."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware

from backend.exception_handlers import register_exception_handlers
from backend.middleware.maintenance import register_maintenance_middleware
from backend.middleware.performance import PerformanceMiddleware
from backend.middleware.request_id import register_request_id_middleware
from backend.middleware.webapp import register_webapp_middleware
from backend.routers.admin_debug import router as admin_debug_router
from backend.routers.site import router as site_router
from backend.routers.tg_update import router as tg_update_router
from config.settings import WEBAPP_DIR, settings
from database.connection import initialize_database
from features.ai.router import router as ai_router
from features.cv.router import router as cv_router
from features.webapp_compat.router import router as webapp_compat_router
from features.obyektivka.router import router as oby_router
from features.payment.router import router as payment_router
from main import create_bot, create_dispatcher

load_dotenv()
logger = logging.getLogger(__name__)


def _cors_origins() -> list[str]:
    origins: list[str] = []
    for raw in (settings.site_base_url, settings.webapp_base):
        url = (raw or "").strip().rstrip("/")
        if url.startswith("http://") or url.startswith("https://"):
            origins.append(url)
    if settings.allow_insecure_auth:
        origins.extend(["http://127.0.0.1:8000", "http://localhost:8000"])
    return origins or ["https://localhost"]


def create_webhook_app() -> FastAPI:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is missing — cannot start webhook application")

    bot = create_bot()
    dp = create_dispatcher()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        report = initialize_database()
        logger.info("Database initialized: %s ok=%s", report.get("db_path"), report.get("ok"))
        app.state.bot = bot
        app.state.dp = dp
        skip_webhook = os.getenv("SKIP_WEBHOOK", "").strip().lower() in ("1", "true", "yes")
        webhook_secret = settings.webhook_secret
        app.state.webhook_secret = webhook_secret
        await bot.delete_webhook(drop_pending_updates=True)
        if settings.webhook_url and not skip_webhook:
            await bot.set_webhook(
                url=settings.webhook_url,
                secret_token=webhook_secret or None,
                drop_pending_updates=True,
            )
            logger.info("Webhook set: %s (secret=%s)", settings.webhook_url, bool(webhook_secret))
        elif skip_webhook:
            logger.info("SKIP_WEBHOOK=1 — polling mode (webhook o'rnatilmadi)")
        from features.admin.jobs import start_admin_jobs
        from shared.bot_commands import register_bot_commands

        await register_bot_commands(bot)
        start_admin_jobs(bot)
        yield
        from features.admin.jobs import stop_admin_jobs

        await stop_admin_jobs()
        from core.redis_client import close_async, close_sync

        await close_async()
        close_sync()
        await bot.session.close()
        logger.info("Webhook application stopped")

    app = FastAPI(
        lifespan=lifespan,
        title="Hujjatchi AI",
        version="3.0",
    )
    cors_origins = _cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=512)
    register_request_id_middleware(app)
    app.add_middleware(PerformanceMiddleware)
    register_webapp_middleware(app)
    register_maintenance_middleware(app)
    register_exception_handlers(app)

    app.include_router(site_router)
    app.include_router(admin_debug_router)
    app.include_router(payment_router)
    app.include_router(cv_router)
    app.include_router(oby_router)
    app.include_router(ai_router)
    app.include_router(webapp_compat_router)
    app.include_router(tg_update_router)

    webapp_path = Path(WEBAPP_DIR)
    if webapp_path.is_dir():
        app.mount("/webapp", StaticFiles(directory=str(webapp_path), html=True), name="webapp")
        logger.info("WebApp mounted at /webapp")
    else:
        logger.error("WebApp directory missing: %s", webapp_path)

    return app
