"""AI voice API routes."""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from core.security import rate_limit
from database.repositories import ai_sessions as sessions_repo
from features.ai.service import process_voice_for_cv
from features.cv import service as cv_service
from shared.auth import resolve_uid

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ai"])


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

    os.makedirs("temp", exist_ok=True)
    ext = os.path.splitext(audio.filename or "")[1] or ".ogg"
    temp_path = os.path.join("temp", f"cv_voice_{uid}_{os.getpid()}{ext}")
    raw = await audio.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Audio bo'sh")
    with open(temp_path, "wb") as fh:
        fh.write(raw)

    try:
        transcript, data, missing = await process_voice_for_cv(temp_path)
        if not data:
            raise HTTPException(status_code=422, detail="Ma'lumot ajratilmadi")
        cv_service.save_user_data(uid, data)
        sessions_repo.create_session(uid, "cv_voice", transcript, data)
        saved = cv_service.get_saved_data(uid) or data
        return {
            "ok": True,
            "data": saved,
            "transcript": transcript[:1200],
            "missing_fields": missing,
        }
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass
