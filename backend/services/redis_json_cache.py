"""
Async Redis JSON helpers for short-TTL API response caching.
Fails open if Redis is down (returns None / no-op) — production-safe on Railway.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def redis_cache_get_json(key: str) -> Optional[dict[str, Any]]:
    try:
        from backend.redis_client import get_redis

        r = get_redis()
        raw = await r.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.debug("redis_cache_get_json miss %s: %s", key, e)
        return None


async def redis_cache_set_json(key: str, data: dict[str, Any], ttl_seconds: int) -> None:
    if ttl_seconds <= 0:
        return
    try:
        from backend.redis_client import get_redis

        r = get_redis()
        await r.set(
            key,
            json.dumps(data, ensure_ascii=False, separators=(",", ":")),
            ex=ttl_seconds,
        )
    except Exception as e:
        logger.debug("redis_cache_set_json skip %s: %s", key, e)


async def redis_cache_delete(key: str) -> None:
    try:
        from backend.redis_client import get_redis

        await get_redis().delete(key)
    except Exception as e:
        logger.debug("redis_cache_delete skip %s: %s", key, e)


def api_me_cache_key(telegram_id: str) -> str:
    return f"web:api_me:v1:{telegram_id}"
