"""Health checks and WebApp entry redirects."""
from __future__ import annotations

import time

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["site"])


@router.get("/health")
async def health():
    return {
        "ok": True,
        "status": "healthy",
        "webapp_mounted": True,
        "time": time.time(),
    }


@router.get("/webapp")
async def webapp_root():
    return RedirectResponse(url="/webapp/index.html")


@router.get("/webapp/")
async def webapp_root_trailing_slash():
    return RedirectResponse(url="/webapp/index.html")


@router.get("/")
async def root():
    return RedirectResponse(url="/webapp/index.html")
