from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.redis_client import get_redis
from backend.routers.jobs import router as jobs_router
from backend.routers.ocr import router as ocr_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm up Redis connection (fail fast in container)
    r = get_redis()
    try:
        await r.ping()
    except Exception:
        # Do not crash the whole app here; existing deployment may not have Redis yet.
        # Celery/Redis will be enforced in docker-compose deployment.
        pass
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Dastyor AI API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(jobs_router)
    app.include_router(ocr_router)
    return app


app = create_app()

