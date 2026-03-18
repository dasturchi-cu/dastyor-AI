from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Literal, Optional

from backend.redis_client import get_redis
from backend.settings import get_settings

JobStatus = Literal["queued", "started", "succeeded", "failed"]


@dataclass(frozen=True, slots=True)
class JobRecord:
    job_id: str
    status: JobStatus
    kind: str
    created_at: int
    updated_at: int
    result_json: Optional[str] = None
    error: Optional[str] = None


def new_job_id() -> str:
    return uuid.uuid4().hex


def _job_key(job_id: str) -> str:
    return f"job:{job_id}"


async def create_job(kind: str, initial: JobStatus = "queued") -> JobRecord:
    now = int(time.time())
    job_id = new_job_id()
    rec = JobRecord(job_id=job_id, status=initial, kind=kind, created_at=now, updated_at=now)
    r = get_redis()
    s = get_settings()
    await r.hset(
        _job_key(job_id),
        mapping={
            "job_id": rec.job_id,
            "status": rec.status,
            "kind": rec.kind,
            "created_at": str(rec.created_at),
            "updated_at": str(rec.updated_at),
            "result_json": "",
            "error": "",
        },
    )
    await r.expire(_job_key(job_id), s.job_ttl_seconds)
    return rec


async def update_job(
    job_id: str,
    *,
    status: JobStatus,
    result: Any | None = None,
    error: str | None = None,
) -> None:
    now = int(time.time())
    r = get_redis()
    mapping: dict[str, str] = {"status": status, "updated_at": str(now)}
    if result is not None:
        mapping["result_json"] = json.dumps(result, ensure_ascii=False)
    if error is not None:
        mapping["error"] = (error or "")[:500]
    await r.hset(_job_key(job_id), mapping=mapping)


async def get_job(job_id: str) -> JobRecord | None:
    r = get_redis()
    data = await r.hgetall(_job_key(job_id))
    if not data:
        return None
    return JobRecord(
        job_id=data.get("job_id") or job_id,
        status=(data.get("status") or "queued"),  # type: ignore[assignment]
        kind=data.get("kind") or "",
        created_at=int(data.get("created_at") or "0"),
        updated_at=int(data.get("updated_at") or "0"),
        result_json=data.get("result_json") or None,
        error=data.get("error") or None,
    )

