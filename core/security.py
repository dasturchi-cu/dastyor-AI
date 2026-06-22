"""Security: validation, rate limiting, path safety."""
from __future__ import annotations

import html
import re
import time
from collections import defaultdict
from pathlib import Path

from fastapi import HTTPException, Request

from config.settings import settings

_RATE_BUCKETS: dict[str, list[float]] = defaultdict(list)
_RATE_MAX_KEYS = 10_000
_SAFE_NAME = re.compile(r"^[a-zA-Z0-9_\-\.]+$")
_PHONE_RE = re.compile(r"^[\d\s+\-()]{7,20}$")
_EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)


def sanitize_text(value: str | None, max_len: int = 500) -> str:
    if not value:
        return ""
    return html.escape(str(value).strip()[:max_len])


def validate_phone(phone: str | None) -> bool:
    return bool(phone and _PHONE_RE.match(phone.strip()))


def validate_email(email: str | None) -> bool:
    if not email:
        return True
    return bool(_EMAIL_RE.match(email.strip()))


def safe_path(base: Path, relative: str) -> Path:
    """Prevent path traversal."""
    target = (base / relative).resolve()
    if not str(target).startswith(str(base.resolve())):
        raise HTTPException(status_code=400, detail="Invalid path")
    return target


def allowed_image(filename: str, content_type: str | None) -> bool:
    fn = (filename or "").lower()
    ct = (content_type or "").lower()
    return fn.endswith((".jpg", ".jpeg", ".png", ".webp")) or ct.startswith("image/")


async def rate_limit(request: Request, key: str | None = None) -> None:
    limit = settings.rate_limit_per_minute
    if limit <= 0:
        return
    client = key or (request.client.host if request.client else "unknown")
    now = time.time()

    from core.redis_client import get_async_redis, is_redis_live, key as redis_key

    if is_redis_live():
        r = await get_async_redis()
        if r:
            bucket = redis_key(f"rate:{client}")
            pipe = r.pipeline()
            pipe.zremrangebyscore(bucket, 0, now - 60)
            pipe.zcard(bucket)
            results = await pipe.execute()
            if int(results[1]) >= limit:
                raise HTTPException(status_code=429, detail="Juda ko'p so'rov. Biroz kuting.")
            await r.zadd(bucket, {str(time.time_ns()): now})
            await r.expire(bucket, 120)
            return

    window = _RATE_BUCKETS[client]
    _RATE_BUCKETS[client] = [t for t in window if now - t < 60]
    if len(_RATE_BUCKETS) > _RATE_MAX_KEYS:
        stale = [k for k, v in _RATE_BUCKETS.items() if not v or now - v[-1] > 120]
        for k in stale[:500]:
            _RATE_BUCKETS.pop(k, None)
    if len(_RATE_BUCKETS[client]) >= limit:
        raise HTTPException(status_code=429, detail="Juda ko'p so'rov. Biroz kuting.")
    _RATE_BUCKETS[client].append(now)
