"""Lightweight observability — structured logging only (no external DB)."""
from __future__ import annotations

import asyncio
import logging
import os
import time
import traceback
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

logger = logging.getLogger("observability")

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
    if not _ENABLED:
        return
    et = (event_type or "")[:40]
    an = (action_name or "")[:160]
    if not et or not an:
        return
    msg = f"{et} {an} status={status} ms={execution_time_ms} user={telegram_id}"
    if error_message:
        logger.warning("%s err=%s meta=%s", msg, error_message[:500], metadata)
    elif et == "HTTP" and execution_time_ms and execution_time_ms >= 800:
        logger.info("%s meta=%s", msg, metadata)
    else:
        logger.debug("%s meta=%s", msg, metadata)


@asynccontextmanager
async def track_span(
    *,
    telegram_id: int | None,
    username: str | None,
    action_name: str,
    metadata: Optional[dict[str, Any]] = None,
) -> AsyncIterator[None]:
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
