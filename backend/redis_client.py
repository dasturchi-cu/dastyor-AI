from __future__ import annotations

from typing import Optional

import redis.asyncio as redis

from backend.settings import get_settings


_redis: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    """
    Shared async Redis client (connection pooled).
    """
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis

