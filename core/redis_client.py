"""Redis connection pool — shared across rate limit, sessions, jobs, FSM."""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_PREFIX = "hujjatchi:"
_sync_client = None
_async_client = None
_redis_checked = False
_redis_ok = False


def key(name: str) -> str:
    return f"{_PREFIX}{name}"


def redis_enabled() -> bool:
    from config.settings import settings

    return settings.use_redis and bool(settings.redis_url)


def _check_sync() -> bool:
    global _redis_checked, _redis_ok
    if _redis_checked:
        return _redis_ok
    _redis_checked = True
    if not redis_enabled():
        _redis_ok = False
        return False
    try:
        client = get_sync_redis()
        _redis_ok = bool(client and client.ping())
        if _redis_ok:
            logger.info("Redis connected (sync)")
        else:
            logger.warning("Redis ping failed — using in-memory fallback")
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — using in-memory fallback", exc)
        _redis_ok = False
    return _redis_ok


def get_sync_redis():
    """Sync Redis client for sessions / voice jobs (thread-safe pool)."""
    global _sync_client
    if not redis_enabled():
        return None
    if _sync_client is None:
        try:
            import redis

            from config.settings import settings

            _sync_client = redis.Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=True,
            )
        except Exception as exc:
            logger.warning("Redis sync client init failed: %s", exc)
            return None
    return _sync_client


async def get_async_redis():
    """Async Redis client for rate limiting."""
    global _async_client
    if not redis_enabled():
        return None
    if _async_client is None:
        try:
            import redis.asyncio as aioredis

            from config.settings import settings

            _async_client = aioredis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
        except Exception as exc:
            logger.warning("Redis async client init failed: %s", exc)
            return None
    return _async_client


def is_redis_live() -> bool:
    return _check_sync()


async def ping_async() -> bool:
    if not redis_enabled():
        return False
    try:
        client = await get_async_redis()
        if client is None:
            return False
        return bool(await client.ping())
    except Exception:
        return False


async def close_async() -> None:
    global _async_client
    if _async_client is not None:
        try:
            await _async_client.aclose()
        except Exception:
            pass
        _async_client = None


def close_sync() -> None:
    global _sync_client, _redis_checked, _redis_ok
    if _sync_client is not None:
        try:
            _sync_client.close()
        except Exception:
            pass
        _sync_client = None
    _redis_checked = False
    _redis_ok = False
