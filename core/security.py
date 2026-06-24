"""Security: validation, rate limiting, path safety."""
from __future__ import annotations

import html
import re
import time
from collections import defaultdict
from pathlib import Path

from fastapi import HTTPException, Request

from config.settings import settings
from shared.security_audit import EVENT_RATE_LIMIT, log_security_event

_RATE_BUCKETS: dict[str, list[float]] = defaultdict(list)
_RATE_MAX_KEYS = 10_000
_SAFE_NAME = re.compile(r"^[a-zA-Z0-9_\-\.]+$")
_PHONE_RE = re.compile(r"^[\d\s+\-()]{7,20}$")
_EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)


def client_ip(request: Request) -> str:
    forwarded = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    if forwarded:
        return forwarded[:64]
    return request.client.host if request.client else "unknown"


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


async def _check_rate_bucket(bucket_key: str, limit: int) -> bool:
    """Return True if request is allowed."""
    if limit <= 0:
        return True
    now = time.time()

    from core.redis_client import get_async_redis, is_redis_live, key as redis_key

    if is_redis_live():
        r = await get_async_redis()
        if r:
            bucket = redis_key(f"rate:{bucket_key}")
            pipe = r.pipeline()
            pipe.zremrangebyscore(bucket, 0, now - 60)
            pipe.zcard(bucket)
            results = await pipe.execute()
            if int(results[1]) >= limit:
                return False
            await r.zadd(bucket, {str(time.time_ns()): now})
            await r.expire(bucket, 120)
            return True

    window = _RATE_BUCKETS[bucket_key]
    _RATE_BUCKETS[bucket_key] = [t for t in window if now - t < 60]
    if len(_RATE_BUCKETS) > _RATE_MAX_KEYS:
        stale = [k for k, v in _RATE_BUCKETS.items() if not v or now - v[-1] > 120]
        for k in stale[:500]:
            _RATE_BUCKETS.pop(k, None)
    if len(_RATE_BUCKETS[bucket_key]) >= limit:
        return False
    _RATE_BUCKETS[bucket_key].append(now)
    return True


async def check_ai_user_quota(user_id: int) -> None:
    """Per-user daily AI request cap."""
    limit = settings.ai_requests_per_user_day
    if limit <= 0 or not user_id:
        return

    from core.redis_client import get_async_redis, is_redis_live, key as redis_key

    bucket = f"ai_day:{user_id}"
    if is_redis_live():
        r = await get_async_redis()
        if r:
            rk = redis_key(bucket)
            count = await r.incr(rk)
            if count == 1:
                await r.expire(rk, 86_400)
            if count > limit:
                from shared.security_audit import EVENT_AI_ABUSE, log_security_event

                log_security_event(
                    EVENT_AI_ABUSE,
                    severity="warn",
                    user_id=user_id,
                    details=f"daily cap {limit} exceeded",
                )
                raise HTTPException(
                    status_code=429,
                    detail="Kunlik AI limiti tugadi. Ertaga qayta urinib ko'ring.",
                )
            return

    # In-memory fallback
    mem_key = f"ai_mem:{user_id}:{time.strftime('%Y%m%d')}"
    _RATE_BUCKETS.setdefault(mem_key, [])
    if len(_RATE_BUCKETS[mem_key]) >= limit:
        from shared.security_audit import EVENT_AI_ABUSE, log_security_event

        log_security_event(EVENT_AI_ABUSE, severity="warn", user_id=user_id)
        raise HTTPException(status_code=429, detail="Kunlik AI limiti tugadi.")
    _RATE_BUCKETS[mem_key].append(time.time())


async def rate_limit(
    request: Request,
    key: str | None = None,
    *,
    user_id: int | None = None,
) -> None:
    """IP + global + per-user rate limits with audit logging."""
    ip = key or client_ip(request)

    checks: list[tuple[str, int]] = [(f"ip:{ip}", settings.rate_limit_per_minute)]
    if settings.global_rate_limit_per_minute > 0:
        checks.append(("global:all", settings.global_rate_limit_per_minute))
    if user_id and settings.rate_limit_per_user_minute > 0:
        checks.append((f"user:{user_id}", settings.rate_limit_per_user_minute))

    for bucket_key, limit in checks:
        if not await _check_rate_bucket(bucket_key, limit):
            log_security_event(
                EVENT_RATE_LIMIT,
                severity="warn",
                ip=ip,
                user_id=user_id,
                details=bucket_key,
            )
            raise HTTPException(status_code=429, detail="Juda ko'p so'rov. Biroz kuting.")
