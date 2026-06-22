"""Obyektivka API routes."""
from __future__ import annotations

import asyncio
import io
import logging
import os
import uuid

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from backend.schemas.webapp import ExportObyektivkaRequest, ObyektivkaRequest, PreviewObyektivkaRequest
from core.security import rate_limit
from database.repositories import obyektivka_data as oby_repo
from features.ai.service import (
    get_missing_oby_fields,
    map_obyektivka_fields,
    process_voice_for_obyektivka,
)
from features.obyektivka import service as oby_service
from shared import async_db
from shared.ai_errors import AI_QUOTA_USER_MSG, AiQuotaError
from shared.auth import resolve_uid_from_webapp
from shared import voice_jobs
from shared.export_delivery import send_bytes_to_telegram

logger = logging.getLogger(__name__)
router = APIRouter(tags=["obyektivka"])


def _uid_from_req(req) -> int:
    uid = resolve_uid_from_webapp(
        getattr(req, "telegram_id", None),
        getattr(req, "token", None),
        getattr(req, "init_data", None),
    )
    if not uid:
        raise HTTPException(status_code=401, detail="Avtorizatsiya talab qilinadi.")
    return uid


async def _run_oby_voice_job(job_id: str, uid: int, raw: bytes, ext: str) -> None:
    os.makedirs("temp", exist_ok=True)
    temp_path = os.path.join("temp", f"oby_voice_{uid}_{uuid.uuid4().hex[:8]}{ext}")
    try:
        with open(temp_path, "wb") as fh:
            fh.write(raw)
        voice_jobs.set_step(job_id, 2)
        transcript, data, missing = await process_voice_for_obyektivka(temp_path)
        if not data:
            voice_jobs.fail_job(job_id, "Ma'lumot ajratilmadi")
            return
        await async_db.run(oby_service.save_pending, uid, data)
        voice_jobs.complete_job(
            job_id,
            data,
            missing,
            max(10, 100 - len(missing) * 8),
            transcript=transcript,
        )
    except AiQuotaError:
        logger.warning("oby voice job %s quota exceeded", job_id)
        voice_jobs.fail_job(job_id, AI_QUOTA_USER_MSG)
    except Exception as e:
        logger.exception("oby voice job %s failed", job_id)
        voice_jobs.fail_job(job_id, str(e)[:200])
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


@router.get("/api/get_oby_data")
async def api_get_oby_data(
    token: str | None = Query(None),
    telegram_id: str | None = Query(None),
) -> dict:
    uid = resolve_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    pending = await async_db.run(oby_service.get_pending, uid)
    saved = await async_db.run(oby_service.get_saved_data, uid) if not pending else None
    data = pending or saved
    if data:
        mapped = map_obyektivka_fields(data)
        missing = get_missing_oby_fields(mapped)
        return {"ok": True, "data": mapped, "missing_fields": missing}
    return {"ok": False}


@router.post("/api/oby_voice_fill")
async def api_oby_voice_fill(
    request: Request,
    audio: UploadFile = File(...),
    telegram_id: str | None = Form(None),
    token: str | None = Form(None),
) -> dict:
    await rate_limit(request)
    uid = resolve_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")

    raw = await audio.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Audio bo'sh")

    ext = os.path.splitext(audio.filename or "")[1] or ".ogg"
    job_id = voice_jobs.create_job(uid, "oby")
    asyncio.create_task(_run_oby_voice_job(job_id, uid, raw, ext))
    return {"ok": True, "job_id": job_id, "step": 1, "status": "running"}


@router.post("/api/oby_text_fill")
async def api_oby_text_fill(body: dict, request: Request) -> dict:
    from database.repositories import ai_sessions as sessions_repo
    from features.ai.service import process_text_for_obyektivka

    await rate_limit(request)
    uid = resolve_uid(str(body.get("telegram_id") or ""), body.get("token"))
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    text = str(body.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Matn bo'sh")
    try:
        transcript, data, missing = await process_text_for_obyektivka(text)
    except AiQuotaError as e:
        raise HTTPException(status_code=503, detail=AI_QUOTA_USER_MSG) from e
    if not data:
        raise HTTPException(status_code=422, detail="Ma'lumot ajratilmadi")
    await async_db.run(oby_service.save_pending, uid, data)
    await async_db.run(sessions_repo.create_session, uid, "oby_text", transcript, data)
    return {
        "ok": True,
        "data": data,
        "transcript": transcript[:1200],
        "missing_fields": missing,
        "fill_percent": max(10, 100 - len(missing) * 8),
    }


@router.get("/api/oby_voice_job/{job_id}")
async def api_oby_voice_job(
    job_id: str,
    telegram_id: str | None = Query(None),
    token: str | None = Query(None),
) -> dict:
    uid = resolve_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    job = voice_jobs.get_job(job_id, uid)
    if not job:
        raise HTTPException(status_code=404, detail="Jarayon topilmadi")
    if job.get("status") == "error":
        raise HTTPException(status_code=422, detail=job.get("error") or "Xatolik")
    return job


@router.post("/api/oby_voice_fill_sync")
async def api_oby_voice_fill_sync(
    request: Request,
    audio: UploadFile = File(...),
    telegram_id: str | None = Form(None),
    token: str | None = Form(None),
) -> dict:
    """Legacy sync endpoint (blocks until AI completes)."""
    await rate_limit(request)
    uid = resolve_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")

    os.makedirs("temp", exist_ok=True)
    ext = os.path.splitext(audio.filename or "")[1] or ".ogg"
    temp_path = os.path.join("temp", f"oby_voice_{uid}_{os.getpid()}{ext}")
    raw = await audio.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Audio bo'sh")
    with open(temp_path, "wb") as fh:
        fh.write(raw)

    try:
        transcript, data, missing = await process_voice_for_obyektivka(temp_path)
        if not data:
            raise HTTPException(status_code=422, detail="Ma'lumot ajratilmadi")
        await async_db.run(oby_service.save_pending, uid, data)
        return {
            "ok": True,
            "data": data,
            "transcript": transcript[:1200],
            "missing_fields": missing,
            "fill_percent": max(10, 100 - len(missing) * 8),
        }
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


@router.post("/api/preview_obyektivka")
async def api_preview_oby(req: PreviewObyektivkaRequest) -> dict:
    import asyncio

    from backend.services.oby_preview_cache import (
        cache_key_for_oby_preview,
        oby_preview_cache_get,
        oby_preview_cache_set,
    )
    from backend.services.render_service import render_obyektivka_html

    payload = req.model_dump(exclude={"telegram_id", "token", "init_data"})
    cache_key = cache_key_for_oby_preview(payload)
    cached = oby_preview_cache_get(cache_key)
    if cached is not None:
        return {"ok": True, "html": cached}
    html = await asyncio.to_thread(
        render_obyektivka_html, payload, watermark=True, mask_pii=True
    )
    oby_preview_cache_set(cache_key, html)
    return {"ok": True, "html": html}


@router.post("/api/export_obyektivka")
async def api_export_oby(req: ExportObyektivkaRequest, request: Request) -> StreamingResponse:
    await rate_limit(request)
    uid = _uid_from_req(req)
    payload = req.model_dump(exclude={"telegram_id", "token", "send_only", "format", "init_data"})
    try:
        docx_bytes, filename = await oby_service.export_docx(uid, payload)
    except PermissionError as e:
        raise HTTPException(status_code=402, detail=str(e)) from e
    except Exception as e:
        logger.exception("export_obyektivka")
        raise HTTPException(status_code=500, detail=str(e)[:200]) from e

    if req.send_only:
        bot = getattr(request.app.state, "bot", None)
        sent = await send_bytes_to_telegram(
            bot,
            uid,
            docx_bytes,
            filename,
            caption="✅ Obyektivka Word tayyor! Keyingi hujjat uchun kredit kerak.",
        )
        if not sent:
            raise HTTPException(status_code=500, detail="Telegramga yuborib bo'lmadi")
        return JSONResponse({"ok": True, "sent": True, "filename": filename})

    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/generate_obyektivka")
async def api_generate_oby(req: ObyektivkaRequest, request: Request) -> StreamingResponse:
    export_req = ExportObyektivkaRequest(**req.model_dump())
    return await api_export_oby(export_req, request)
