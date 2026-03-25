"""
Real-time debug + error tracking (observability).

Writes to Supabase public.system_logs using fire-and-forget pattern.

Features:
- track_event_fire_and_forget: single event (CLICK/START/END/ERROR/HTTP)
- track_span: context manager that emits START and END/ERROR with duration_ms
- optional Redis span correlation id (future), minimal overhead now
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
import traceback
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

logger = logging.getLogger(__name__)

_ENABLED = os.getenv("SYSTEM_LOG_ENABLED", "1").strip().lower() not in ("0", "false", "no")
_STACK = os.getenv("SYSTEM_LOG_STACKTRACE", "1").strip().lower() not in ("0", "false", "no")


def track_event_fire_and_forget(
    *,
    telegram_id: int | None,
    username: str | None,
    event_type: str,
    action_name: str,
    status: str | None = None,
    error_message: str | None = None,
    execution_time_ms: int | None = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """
    Fire-and-forget insert into system_logs. Never blocks user requests.
    """
    if not _ENABLED:
        return
    et = (event_type or "")[:40]
    an = (action_name or "")[:160]
    if not et or not an:
        return

    md = dict(metadata) if isinstance(metadata, dict) else None

    async def _run():
        try:
            from bot.services.supabase_db import db_insert_system_log, has_db

            if not has_db():
                return
            await asyncio.to_thread(
                db_insert_system_log,
                telegram_id,
                username,
                et,
                an,
                status,
                error_message,
                execution_time_ms,
                md,
            )
        except Exception:
            logger.debug("track_event skipped et=%s an=%s", et, an, exc_info=True)

    try:
        asyncio.get_running_loop().create_task(_run())
    except Exception:
        # no running loop; do nothing (rare in this codebase)
        pass


@asynccontextmanager
async def track_span(
    *,
    telegram_id: int | None,
    username: str | None,
    action_name: str,
    metadata: Optional[dict[str, Any]] = None,
) -> AsyncIterator[None]:
    """
    Emits:
    - START action_name
    - END success with execution_time_ms
    - ERROR failed with execution_time_ms + error + optional stacktrace
    """
    t0 = time.perf_counter()
    track_event_fire_and_forget(
        telegram_id=telegram_id,
        username=username,
        event_type="START",
        action_name=action_name,
        status="ok",
        metadata=metadata,
    )
    try:
        yield
        dt = int((time.perf_counter() - t0) * 1000)
        track_event_fire_and_forget(
            telegram_id=telegram_id,
            username=username,
            event_type="END",
            action_name=action_name,
            status="success",
            execution_time_ms=dt,
            metadata=metadata,
        )
    except Exception as e:
        dt = int((time.perf_counter() - t0) * 1000)
        md = dict(metadata) if isinstance(metadata, dict) else {}
        if _STACK:
            md["stack"] = traceback.format_exc(limit=20)[-8000:]
        track_event_fire_and_forget(
            telegram_id=telegram_id,
            username=username,
            event_type="ERROR",
            action_name=action_name,
            status="failed",
            error_message=str(e)[:2000],
            execution_time_ms=dt,
            metadata=md or None,
        )
        raise

