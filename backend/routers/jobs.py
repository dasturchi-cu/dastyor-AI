from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException

from backend.celery_app import celery_app
from backend.jobs import QueueUnavailableError, get_job, update_job


router = APIRouter(prefix="/api", tags=["jobs"])


@router.get("/jobs/{job_id}")
async def api_get_job(job_id: str) -> dict[str, Any]:
    try:
        rec = await get_job(job_id)
    except QueueUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e)[:200])
    if rec is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # If Redis doesn't have a terminal status yet, try to sync from Celery backend.
    if rec.status in ("queued", "started"):
        try:
            ar = celery_app.AsyncResult(job_id)
            if ar.successful():
                await update_job(job_id, status="succeeded", result=ar.result)
                rec = await get_job(job_id) or rec
            elif ar.failed():
                await update_job(job_id, status="failed", error=str(ar.result))
                rec = await get_job(job_id) or rec
            elif ar.status == "STARTED":
                await update_job(job_id, status="started")
                rec = await get_job(job_id) or rec
        except Exception:
            # If Celery is not configured/running yet, just return Redis snapshot.
            pass

    payload: dict[str, Any] = {
        "job_id": rec.job_id,
        "status": rec.status,
        "kind": rec.kind,
        "created_at": rec.created_at,
        "updated_at": rec.updated_at,
    }
    if rec.error:
        payload["error"] = rec.error
    if rec.result_json:
        try:
            import json

            payload["result"] = json.loads(rec.result_json)
        except Exception:
            payload["result"] = rec.result_json
    return payload

