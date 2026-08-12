"""CV API routes."""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from backend.schemas.webapp import CVRequest, ExportCVRequest
from backend.services.cv_preview_cache import (
    cache_key_for_cv_preview,
    cv_preview_cache_get,
    cv_preview_cache_set,
)
from core.security import rate_limit
from features.ai.service import count_cv_populated_fields
from features.cv import service as cv_service
from features.cv.render import preview_html
from database.repositories import users as users_repo
from shared import async_db
from shared.auth import resolve_uid_from_webapp
from shared.export_delivery import send_bytes_to_telegram

logger = logging.getLogger(__name__)
router = APIRouter(tags=["cv"])


def _uid_from_req(req) -> int:
    uid = resolve_uid_from_webapp(
        getattr(req, "telegram_id", None),
        getattr(req, "token", None),
        getattr(req, "init_data", None),
    )
    if not uid:
        raise HTTPException(status_code=401, detail="Avtorizatsiya talab qilinadi.")
    return uid


@router.get("/api/cv_saved_data")
async def api_cv_saved(
    telegram_id: str | None = None,
    token: str | None = None,
    init_data: str | None = None,
) -> dict:
    uid = resolve_uid_from_webapp(telegram_id, token, init_data)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    from database.repositories import cv_data as cv_repo

    data = await async_db.run(cv_repo.get, uid)
    return {"ok": True, "data": data or {}}


@router.post("/api/cv_preview_html")
async def api_cv_preview(req: ExportCVRequest, request: Request) -> HTMLResponse:
    uid = resolve_uid_from_webapp(req.telegram_id, req.token, req.init_data)
    if not uid:
        raise HTTPException(status_code=401, detail="Avtorizatsiya talab qilinadi.")
    await rate_limit(request, user_id=uid)
    data = req.model_dump(exclude={"telegram_id", "token", "send_only", "format"})
    cache_key = cache_key_for_cv_preview(data)
    cached = cv_preview_cache_get(cache_key)
    if cached is not None:
        return HTMLResponse(content=cached, media_type="text/html; charset=utf-8")
    html = await asyncio.to_thread(preview_html, data)
    cv_preview_cache_set(cache_key, html)
    return HTMLResponse(content=html, media_type="text/html; charset=utf-8")


def _cv_export_is_acceptable(payload: dict) -> bool:
    return count_cv_populated_fields(payload) >= 1 and bool(str(payload.get("name") or "").strip())


@router.post("/api/export_cv")
async def api_export_cv(req: ExportCVRequest, request: Request) -> Response:
    await rate_limit(request)
    uid = _uid_from_req(req)
    from shared.subscription import ensure_user_subscribed_api
    await ensure_user_subscribed_api(request, uid)
    payload = req.model_dump(exclude={"telegram_id", "token", "send_only", "format", "init_data"})
    if not _cv_export_is_acceptable(payload):
        raise HTTPException(
            status_code=400,
            detail="Forma to'ldirilmagan — avval ism va boshqa ma'lumotlarni kiriting.",
        )
    bot = getattr(request.app.state, "bot", None)
    try:
        pdf_bytes, filename = await cv_service.export_pdf(uid, payload, bot)
    except PermissionError as e:
        raise HTTPException(status_code=402, detail=str(e)) from e
    except Exception as e:
        logger.exception("export_cv")
        raise HTTPException(status_code=500, detail=str(e)[:200]) from e

    if req.send_only:
        bot = getattr(request.app.state, "bot", None)
        left = await async_db.run(users_repo.get_credits, uid)
        left_txt = f"Qoldi: <b>{left}</b> ta." if left > 0 else "Yuklashlar tugadi — yangi paket tanlang."
        sent = await send_bytes_to_telegram(
            bot,
            uid,
            pdf_bytes,
            filename,
            caption=f"✅ CV PDF tayyor! {left_txt}",
            with_referral_share=False,
        )
        if not sent:
            raise HTTPException(status_code=500, detail="Telegramga yuborib bo'lmadi")
        return JSONResponse({"ok": True, "sent": True, "filename": filename, "credits_left": left})

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/generate_cv")
async def api_generate_cv(req: CVRequest, request: Request) -> Response:
    export_req = ExportCVRequest(**req.model_dump())
    return await api_export_cv(export_req, request)
