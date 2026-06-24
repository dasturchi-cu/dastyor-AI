"""Background health checker — re-probes cooled-down endpoints."""
from __future__ import annotations

import asyncio
import logging
import threading

from features.ai.routing.adapters import probe_endpoint
from features.ai.routing.config import load_routing_config
from features.ai.routing.cooldown import get_cooldown_registry
from features.ai.routing.pool import get_endpoint_pool
from features.ai.routing.types import Endpoint, ProviderName

logger = logging.getLogger(__name__)

_CHECK_INTERVAL_SEC = 60
_task: asyncio.Task | None = None
_stop_event: asyncio.Event | None = None
_thread_local_started = False


async def _health_loop() -> None:
    global _stop_event
    _stop_event = asyncio.Event()
    cfg = load_routing_config()
    pool = get_endpoint_pool()
    cooldown = get_cooldown_registry(cfg.cooldown_ms)

    while _stop_event and not _stop_event.is_set():
        try:
            active_cooldowns = cooldown.list_active()
            if active_cooldowns:
                for item in active_cooldowns:
                    provider = ProviderName(item["provider"])
                    key_index = int(item["key_index"])
                    pcfg = cfg.providers.get(provider)
                    if not pcfg or key_index < 1 or key_index > len(pcfg.api_keys):
                        continue
                    api_key = pcfg.api_keys[key_index - 1]
                    model = pcfg.models[0] if pcfg.models else ""
                    ep = Endpoint(
                        provider=provider,
                        key_index=key_index,
                        model=model,
                        api_key=api_key,
                        extras=dict(pcfg.extras),
                    )
                    ok = await probe_endpoint(ep, timeout_sec=12.0)
                    if ok:
                        cooldown.clear(provider, key_index)
                        pool.record_success(ep)
                        try:
                            from features.ai.routing.quota import get_quota_monitor

                            get_quota_monitor().record_success(
                                provider.value, key_index, model
                            )
                        except Exception:
                            pass
                        logger.info(
                            "Health recovery: %s key#%s back in pool",
                            provider.value,
                            key_index,
                        )
        except Exception as e:
            logger.warning("Health checker iteration error: %s", e)

        try:
            from features.ai.routing.quota import get_quota_monitor

            get_quota_monitor().snapshot_all()
        except Exception as e:
            logger.debug("Quota snapshot skipped: %s", e)

        try:
            await asyncio.wait_for(_stop_event.wait(), timeout=_CHECK_INTERVAL_SEC)
        except asyncio.TimeoutError:
            pass


def start_health_checker() -> None:
    global _task, _thread_local_started
    if _task and not _task.done():
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.debug("No running event loop — health checker starts on first loop")
        return

    _task = loop.create_task(_health_loop(), name="ai-health-checker")
    _thread_local_started = True
    logger.info("AI health checker started (interval=%ss)", _CHECK_INTERVAL_SEC)


async def stop_health_checker() -> None:
    global _task, _stop_event
    if _stop_event:
        _stop_event.set()
    if _task:
        try:
            await asyncio.wait_for(_task, timeout=5.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            _task.cancel()
        _task = None
    logger.info("AI health checker stopped")
