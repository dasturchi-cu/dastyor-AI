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
from starlette.middleware.gzip import GZipMiddleware

from backend.middleware.performance import PerformanceMiddleware
from backend.middleware.maintenance import register_maintenance_middleware

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

        # Telegram chap yuqori "App" / menu — BotFatherda eski host (masalan onrender) qolgan bo'lsa,
        # brauzerda Railway ochiladi, lekin bot ichida Not Found. Env bilan menyuni yangilaymiz.
        if os.getenv("SYNC_TELEGRAM_MENU_WEBAPP", "1").strip().lower() not in ("0", "false", "no"):
            try:
                from telegram import MenuButtonWebApp, WebAppInfo

                # Har doim jarayon muhitidan o'qimiz (web_constants import vaqti eski bo'lishi mumkin)
                override = os.getenv("MENU_WEBAPP_URL", "").strip()
                base = os.getenv("WEBAPP_BASE", "").strip().rstrip("/")
                if override:
                    menu_url = override
                elif base:
                    menu_url = f"{base}/index.html"
                else:
                    menu_url = ""

                if menu_url.startswith("https://"):
                    btn_text = (os.getenv("MENU_WEBAPP_TEXT", "Dastyor Ai") or "Dastyor Ai").strip()[:64]
                    await application.bot.set_chat_menu_button(
                        menu_button=MenuButtonWebApp(
                            text=btn_text,
                            web_app=WebAppInfo(url=menu_url),
                        ),
                    )
                    logger.info("Telegram default menu WebApp URL set to: %s", menu_url)
                    try:
                        cur = await application.bot.get_chat_menu_button()
                        wurl = getattr(
                            getattr(cur, "web_app", None),
                            "url",
                            None,
                        )
                        logger.info("Telegram get_chat_menu_button confirms web_app.url=%s", wurl)
                    except Exception as ver_e:
                        logger.warning("get_chat_menu_button verify failed: %s", ver_e)
                else:
                    logger.warning(
                        "Menu WebApp not synced: set WEBAPP_BASE=https://.../webapp (hozir env bo'sh). "
                        "Railway Variables da WEBAPP_BASE borligini tekshiring."
                    )
            except Exception as e:
                logger.warning("set_chat_menu_button skipped: %s", e)

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
    # JSON/HTML responses: kamroq tarmoq va tezroq yuklash (WebApp API).
    app.add_middleware(GZipMiddleware, minimum_size=512)
    # So‘rov vaqti: X-Process-Time-ms + sekin yo‘llar uchun log.
    app.add_middleware(PerformanceMiddleware)
    register_webapp_middleware(app)
    # Maintenance must be early: block web/api fast.
    register_maintenance_middleware(app)
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
