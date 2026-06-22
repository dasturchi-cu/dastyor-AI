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
from backend.routers.site import router as site_router
from backend.routers.tg_update import router as tg_update_router
from config.settings import WEBAPP_DIR, settings
from database.connection import init_db
from features.ai.router import router as ai_router
from features.cv.router import router as cv_router
from features.legacy.router import router as legacy_router
from features.obyektivka.router import router as oby_router
from features.payment.router import router as payment_router
from main import create_bot, create_dispatcher

load_dotenv()
logger = logging.getLogger(__name__)


def create_webhook_app() -> FastAPI:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is missing — cannot start webhook application")

    bot = create_bot()
    dp = create_dispatcher()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db()
        app.state.bot = bot
        app.state.dp = dp
        skip_webhook = os.getenv("SKIP_WEBHOOK", "").strip().lower() in ("1", "true", "yes")
        await bot.delete_webhook(drop_pending_updates=True)
        if settings.webhook_url and not skip_webhook:
            await bot.set_webhook(url=settings.webhook_url, drop_pending_updates=True)
            logger.info("Webhook set: %s", settings.webhook_url)
        elif skip_webhook:
            logger.info("SKIP_WEBHOOK=1 — polling mode (webhook o'rnatilmadi)")
        yield
        await bot.session.close()
        logger.info("Webhook application stopped")

    app = FastAPI(
        lifespan=lifespan,
        title="Hujjatchi AI",
        version="3.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=512)
    register_request_id_middleware(app)
    app.add_middleware(PerformanceMiddleware)
    register_webapp_middleware(app)
    register_maintenance_middleware(app)
    register_exception_handlers(app)

    app.include_router(site_router)
    app.include_router(payment_router)
    app.include_router(cv_router)
    app.include_router(oby_router)
    app.include_router(ai_router)
    app.include_router(legacy_router)
    app.include_router(tg_update_router)

    webapp_path = Path(WEBAPP_DIR)
    if webapp_path.is_dir():
        app.mount("/webapp", StaticFiles(directory=str(webapp_path), html=True), name="webapp")
        logger.info("WebApp mounted at /webapp")
    else:
        logger.error("WebApp directory missing: %s", webapp_path)

    return app
