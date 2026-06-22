"""Async voice-fill jobs — Redis primary, in-memory fallback."""
from __future__ import annotations

import json
import threading
import time
import uuid
from typing import Any

from core.redis_client import get_sync_redis, is_redis_live, key

_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}
_TTL_SECONDS = 600


def _purge_stale() -> None:
    now = time.monotonic()
    stale = [k for k, v in _jobs.items() if now - float(v.get("ts", now)) > _TTL_SECONDS]
    for k in stale:
        _jobs.pop(k, None)


def _job_key(job_id: str) -> str:
    return key(f"voice_job:{job_id}")


def _redis_get(job_id: str) -> dict[str, Any] | None:
    r = get_sync_redis()
    if not r:
        return None
    raw = r.get(_job_key(job_id))
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _redis_set(job_id: str, job: dict[str, Any]) -> None:
    r = get_sync_redis()
    if not r:
        return
    payload = {k: v for k, v in job.items() if k != "ts"}
    r.setex(_job_key(job_id), int(_TTL_SECONDS), json.dumps(payload, ensure_ascii=False))


def _new_job(uid: int, kind: str) -> dict[str, Any]:
    return {
        "id": "",
        "uid": int(uid),
        "kind": kind,
        "step": 1,
        "status": "running",
        "data": None,
        "missing_fields": [],
        "fill_percent": 0,
        "transcript": "",
        "error": None,
        "ts": time.monotonic(),
    }


def create_job(uid: int, kind: str = "oby") -> str:
    job_id = uuid.uuid4().hex
    job = _new_job(uid, kind)
    job["id"] = job_id

    if is_redis_live():
        _redis_set(job_id, job)
        return job_id

    with _lock:
        _purge_stale()
        _jobs[job_id] = job
    return job_id


def _update(job_id: str, updater) -> None:
    if is_redis_live():
        job = _redis_get(job_id)
        if not job:
            return
        updater(job)
        _redis_set(job_id, job)
        return

    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        updater(job)
        job["ts"] = time.monotonic()


def set_step(job_id: str, step: int, **extra: Any) -> None:
    def _apply(job: dict[str, Any]) -> None:
        job["step"] = int(step)
        job.update(extra)

    _update(job_id, _apply)


def complete_job(
    job_id: str,
    data: dict,
    missing_fields: list,
    fill_percent: int,
    transcript: str = "",
    *,
    populated_fields: int | None = None,
) -> None:
    if populated_fields is not None and populated_fields < 1:
        fail_job(job_id, "Ma'lumot ajratilmadi")
        return
    set_step(
        job_id,
        3,
        status="done",
        data=data,
        missing_fields=missing_fields,
        fill_percent=fill_percent,
        transcript=transcript[:1200],
        populated_fields=populated_fields or 0,
    )


def fail_job(job_id: str, error: str) -> None:
    set_step(job_id, 0, status="error", error=str(error)[:300])


def get_job(job_id: str, uid: int) -> dict[str, Any] | None:
    if is_redis_live():
        job = _redis_get(job_id)
    else:
        with _lock:
            job = _jobs.get(job_id)

    if not job or int(job.get("uid") or 0) != int(uid):
        return None

    out = {k: v for k, v in job.items() if k != "ts"}
    if out.get("data") is not None:
        out["ok"] = True
    return out
