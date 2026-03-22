from __future__ import annotations

import base64
import io
import os
from typing import Any, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from backend.celery_app import celery_app
from backend.jobs import create_job, get_job, update_job
from backend.services.upload_io import EmptyUploadError, UploadTooLargeError, read_upload_limited
from backend.services.user_resolve import resolve_telegram_uid
from backend.services.web_quota import web_quota_after, web_quota_before


router = APIRouter(prefix="/api", tags=["ocr"])


def _ocr_use_celery() -> bool:
    return os.getenv("OCR_USE_CELERY", "0").strip().lower() in ("1", "true", "yes")


@router.post("/ocr")
async def api_ocr(
    file: UploadFile = File(...),
    telegram_id: Optional[str] = Form(None),
    token: Optional[str] = Form(None),
) -> dict[str, Any]:
    """
    Matn ajratish: default — sinxron Paddle (Celery worker shart emas).
    OCR_USE_CELERY=1 bo'lsa — navbat (job_id + /api/jobs/{id}).
    telegram_id + token (ixtiyoriy) — WebApp: OCR limiti hisoblanadi.
    """
    uid_str = resolve_telegram_uid(telegram_id, token)
    uid_int = int(uid_str) if uid_str else None

    try:
        raw = await read_upload_limited(file)
    except EmptyUploadError:
        raise HTTPException(status_code=400, detail="Empty file")
    except UploadTooLargeError:
        raise HTTPException(status_code=400, detail="File too large")

    if _ocr_use_celery():
        job = await create_job("ocr:text")
        celery_app.send_task("ocr.extract_text", args=[raw], kwargs={}, task_id=job.job_id)
        return {"ok": True, "job_id": job.job_id}

    if uid_int:
        from bot.services.plan_limits import CAT_OCR

        web_quota_before(uid_int, CAT_OCR)

    from backend.services.paddle_ocr_runtime import ocr_extract_text_from_bytes

    loop = __import__("asyncio").get_running_loop()
    try:
        result = await loop.run_in_executor(None, lambda: ocr_extract_text_from_bytes(raw))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR xatosi: {str(e)[:200]}")
    r = result or {}
    payload: dict[str, Any] = {
        "ok": True,
        "text": r.get("text") or "",
        "lines": r.get("lines"),
    }
    if r.get("html_layout"):
        payload["html_layout"] = r["html_layout"]
    if r.get("width") is not None:
        payload["width"] = r["width"]
    if r.get("height") is not None:
        payload["height"] = r["height"]
    if r.get("preprocess"):
        payload["preprocess"] = r["preprocess"]
    if uid_int and (payload.get("text") or "").strip():
        from bot.services.plan_limits import CAT_OCR

        payload["quota"] = web_quota_after(uid_int, CAT_OCR, "Web API OCR")
    return payload


@router.post("/ocr-word")
async def api_ocr_word_enqueue(file: UploadFile = File(...)) -> Any:
    try:
        raw = await read_upload_limited(file)
    except EmptyUploadError:
        raise HTTPException(status_code=400, detail="Empty file")
    except UploadTooLargeError:
        raise HTTPException(status_code=400, detail="File too large")

    if _ocr_use_celery():
        job = await create_job("ocr:docx")
        celery_app.send_task("ocr.image_to_docx", args=[raw], kwargs={}, task_id=job.job_id)
        return {"ok": True, "job_id": job.job_id}

    from backend.services.paddle_ocr_runtime import ocr_image_to_docx_from_bytes

    loop = __import__("asyncio").get_running_loop()
    try:
        payload = await loop.run_in_executor(None, lambda: ocr_image_to_docx_from_bytes(raw))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR Word xatosi: {str(e)[:200]}")
    b64 = (payload or {}).get("docx_b64")
    if not b64:
        raise HTTPException(status_code=500, detail="DOCX yaratilmadi")
    docx_bytes = base64.b64decode(b64)
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="ocr_result.docx"'},
    )


@router.get("/ocr-word/{job_id}")
async def api_ocr_word_download(job_id: str):
    rec = await get_job(job_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if rec.status != "succeeded" or not rec.result_json:
        raise HTTPException(status_code=409, detail="Job not ready")
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
