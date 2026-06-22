"""In-memory async voice-fill jobs (instant HTTP ack + client polling)."""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any

_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}
_TTL_SECONDS = 600.0


def _purge_stale() -> None:
    now = time.monotonic()
    stale = [k for k, v in _jobs.items() if now - float(v.get("ts", now)) > _TTL_SECONDS]
    for k in stale:
        _jobs.pop(k, None)


def create_job(uid: int, kind: str = "oby") -> str:
    job_id = uuid.uuid4().hex
    with _lock:
        _purge_stale()
        _jobs[job_id] = {
            "id": job_id,
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
    return job_id


def set_step(job_id: str, step: int, **extra: Any) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job["step"] = int(step)
        job["ts"] = time.monotonic()
        job.update(extra)


def complete_job(
    job_id: str,
    data: dict,
    missing_fields: list,
    fill_percent: int,
    transcript: str = "",
) -> None:
    set_step(
        job_id,
        3,
        status="done",
        data=data,
        missing_fields=missing_fields,
        fill_percent=fill_percent,
        transcript=transcript[:1200],
    )


def fail_job(job_id: str, error: str) -> None:
    set_step(job_id, 0, status="error", error=str(error)[:300])


def get_job(job_id: str, uid: int) -> dict[str, Any] | None:
    with _lock:
        job = _jobs.get(job_id)
        if not job or int(job.get("uid") or 0) != int(uid):
            return None
        out = {k: v for k, v in job.items() if k != "ts"}
        if out.get("data") is not None:
            out["ok"] = True
        return out
