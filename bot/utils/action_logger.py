"""
Universal async, fire-and-forget action logger.

Goals:
- log EVERYTHING with low overhead
- avoid duplicates (dedupe window)
- never break user flow (fail open)

Storage:
- primary: Supabase public.action_logs (uuid)
- optional dedupe: Redis SETNX with TTL (fast, cross-process)
- fallback dedupe: in-memory TTL (per-process)
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DEDUP_TTL = int(os.getenv("ACTION_LOG_DEDUP_TTL_SECONDS", "8") or "8")
_USE_REDIS = os.getenv("ACTION_LOG_USE_REDIS", "1").strip().lower() not in ("0", "false", "no")

_mem: dict[str, float] = {}
_mem_lock = asyncio.Lock()


def _dedupe_key(telegram_id: int, action_type: str, details: str | None, metadata: dict | None) -> str:
    blob = {
        "u": int(telegram_id),
        "a": str(action_type or ""),
        "d": (details or "")[:300],
        "m": metadata or {},
    }
    raw = json.dumps(blob, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "actlog:" + hashlib.sha256(raw).hexdigest()


async def _dedupe_allow(key: str) -> bool:
    """
    Returns True if we should log; False if duplicate within TTL.
    """
    if _DEDUP_TTL <= 0:
        return True

    now = time.monotonic()

    # 1) Redis cross-process dedupe
    if _USE_REDIS:
        try:
            from backend.redis_client import get_redis

            r = get_redis()
            # SET key "1" NX EX ttl
            ok = await r.set(key, "1", ex=_DEDUP_TTL, nx=True)
            if ok:
                return True
            return False
        except Exception:
            # fall back to in-memory
            pass

    # 2) in-memory TTL dedupe
    async with _mem_lock:
        # cleanup small, bounded
        if len(_mem) > 2048:
            cutoff = now - max(_DEDUP_TTL, 5)
            for k, ts in list(_mem.items())[:512]:
                if ts < cutoff:
                    _mem.pop(k, None)
        ts = _mem.get(key)
        if ts and now - ts < _DEDUP_TTL:
            return False
        _mem[key] = now
        return True


async def _insert_log_sync(
    telegram_id: int,
    username: str | None,
    action_type: str,
    details: str | None,
    metadata: dict | None,
) -> None:
    """
    Supabase client is sync → run in thread.
    """
    from bot.services.supabase_db import db_insert_action_log_v2, has_db

    if not has_db():
        return
    db_insert_action_log_v2(
        telegram_id=telegram_id,
        username=username,
        action_type=action_type,
        details=details,
        metadata=metadata,
    )


def log_action_fire_and_forget(
    *,
    telegram_id: int,
    username: str | None,
    action_type: str,
    details: str | None = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """
    Public API (non-blocking). Safe to call from bot handlers and web routes.
    """
    try:
        uid = int(telegram_id)
    except Exception:
        return
    a = str(action_type or "")[:120]
    if not a:
        return

    # Keep payload small
    md: dict | None = dict(metadata) if isinstance(metadata, dict) else None
    det = (details or "")[:2000] if details is not None else None
    uname = (username or "")[:128] if username is not None else None

    key = _dedupe_key(uid, a, det, md)

    async def _run():
        try:
            if not await _dedupe_allow(key):
                return
            await asyncio.to_thread(_insert_log_sync, uid, uname, a, det, md)
        except Exception:
            logger.debug("log_action skipped (uid=%s a=%s)", uid, a, exc_info=True)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_run())
    except Exception:
        # no loop → best effort sync (rare in this project)
        try:
            import threading

            threading.Thread(target=lambda: asyncio.run(_run()), daemon=True).start()
        except Exception:
            pass

