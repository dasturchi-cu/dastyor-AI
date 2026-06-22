"""AI voice + text API routes."""
from __future__ import annotations

import asyncio
import logging
import os
import uuid

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel

from core.security import rate_limit
from database.repositories import ai_sessions as sessions_repo
from features.ai.service import (
    process_text_for_cv,
    process_voice_for_cv,
)
from features.cv import service as cv_service
from shared import async_db
from shared.ai_errors import AI_QUOTA_USER_MSG, AiQuotaError
from shared.auth import resolve_uid
from shared import voice_jobs

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ai"])


class TextFillRequest(BaseModel):
    telegram_id: int | None = None
    token: str | None = None
    text: str = ""


async def _run_cv_voice_job(job_id: str, uid: int, temp_path: str) -> None:
    try:
        voice_jobs.set_step(job_id, 2)
        transcript, data, missing = await process_voice_for_cv(temp_path)
        if not data:
            voice_jobs.fail_job(job_id, "Ma'lumot ajratilmadi")
            return
        await async_db.run(cv_service.save_user_data, uid, data)
        voice_jobs.complete_job(
            job_id,
            data,
            missing,
            max(10, 100 - len(missing) * 12),
            transcript=transcript,
        )
    except AiQuotaError:
        logger.exception("cv voice job %s quota", job_id)
        voice_jobs.fail_job(job_id, AI_QUOTA_USER_MSG)
    except Exception as e:
        logger.exception("cv voice job %s failed", job_id)
        voice_jobs.fail_job(job_id, str(e)[:200])
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


@router.post("/api/cv_voice_fill")
async def api_cv_voice_fill(
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

    os.makedirs("temp", exist_ok=True)
    ext = os.path.splitext(audio.filename or "")[1] or ".ogg"
    temp_path = os.path.join("temp", f"cv_voice_{uid}_{uuid.uuid4().hex[:8]}{ext}")
    with open(temp_path, "wb") as fh:
        fh.write(raw)

    job_id = voice_jobs.create_job(uid, "cv")
    asyncio.create_task(_run_cv_voice_job(job_id, uid, temp_path))
    return {"ok": True, "job_id": job_id, "step": 1, "status": "running"}


@router.get("/api/cv_voice_job/{job_id}")
async def api_cv_voice_job(
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


@router.post("/api/cv_text_fill")
async def api_cv_text_fill(body: TextFillRequest, request: Request) -> dict:
    await rate_limit(request)
    uid = resolve_uid(
        str(body.telegram_id) if body.telegram_id else None,
        body.token,
    )
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")

    try:
        transcript, data, missing = await process_text_for_cv(body.text)
    except AiQuotaError as e:
        raise HTTPException(status_code=503, detail=AI_QUOTA_USER_MSG) from e
    if not data or len(missing) > 6:
        raise HTTPException(status_code=422, detail="CV uchun yetarli ma'lumot topilmadi")
    cv_service.save_user_data(uid, data)
    sessions_repo.create_session(uid, "cv_text", transcript, data)
    saved = cv_service.get_saved_data(uid) or data
    return {
        "ok": True,
        "data": saved,
        "transcript": transcript[:1200],
        "missing_fields": missing,
        "fill_percent": max(10, 100 - len(missing) * 12),
    }
