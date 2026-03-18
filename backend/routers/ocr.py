from __future__ import annotations

import base64
import io
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from backend.celery_app import celery_app
from backend.jobs import create_job, get_job, update_job
from backend.settings import get_settings


router = APIRouter(prefix="/api", tags=["ocr"])


@router.post("/ocr")
async def api_ocr_enqueue(file: UploadFile = File(...)) -> dict[str, Any]:
    settings = get_settings()
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(status_code=400, detail="File too large")

    job = await create_job("ocr:text")
    # enqueue celery
    celery_app.send_task("ocr.extract_text", args=[raw], kwargs={}, task_id=job.job_id)
    return {"ok": True, "job_id": job.job_id}


@router.post("/ocr-word")
async def api_ocr_word_enqueue(file: UploadFile = File(...)) -> dict[str, Any]:
    settings = get_settings()
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(status_code=400, detail="File too large")

    job = await create_job("ocr:docx")
    celery_app.send_task("ocr.image_to_docx", args=[raw], kwargs={}, task_id=job.job_id)
    return {"ok": True, "job_id": job.job_id}


@router.get("/ocr-word/{job_id}")
async def api_ocr_word_download(job_id: str):
    rec = await get_job(job_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if rec.status != "succeeded" or not rec.result_json:
        raise HTTPException(status_code=409, detail="Job not ready")
    # result_json is produced by update_job; for now we also accept celery backend via polling step (see below)
    import json

    try:
        payload = json.loads(rec.result_json)
    except Exception:
        raise HTTPException(status_code=500, detail="Corrupt job result")
    b64 = payload.get("docx_b64")
    if not b64:
        raise HTTPException(status_code=404, detail="DOCX not found")
    docx_bytes = base64.b64decode(b64)
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="ocr_result.docx"'},
    )

