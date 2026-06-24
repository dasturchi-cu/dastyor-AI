"""Multi-provider AI failover engine."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from features.ai.routing.adapters import generate_with_endpoint
from features.ai.routing.config import load_routing_config
from features.ai.routing.cooldown import get_cooldown_registry
from features.ai.routing.pool import get_endpoint_pool
from features.ai.routing.types import Endpoint, ProviderName, RequestStatus
from shared.ai_errors import AiQuotaError, is_failover_error, is_quota_error

logger = logging.getLogger(__name__)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def generate_text_with_failover(
    prompt: str,
    *,
    preferred_models: list[str] | None = None,
    timeout: int | None = None,
) -> str:
    """
    Autonomous failover across providers, keys, and models.
    Never interrupts the user — tries full chain before raising.
    """
    cfg = load_routing_config()
    pool = get_endpoint_pool()
    cooldown = get_cooldown_registry(cfg.cooldown_ms)
    timeout_sec = (timeout if timeout is not None else cfg.request_timeout_ms // 1000) or 35

    chain = pool.iter_failover_chain(preferred_models=preferred_models)
    if not chain:
        raise AiQuotaError("No AI providers configured — check API keys in .env")

    last_error = "All providers exhausted"
    attempts = 0
    max_attempts = max(len(chain), cfg.max_retries + 1)

    for endpoint in chain:
        if attempts >= max_attempts * 10:
            break
        attempts += 1

        if cooldown.is_cooling(endpoint.provider, endpoint.key_index):
            continue

        request_time = _utc_iso()
        t0 = time.perf_counter()

        try:
            result = await generate_with_endpoint(endpoint, prompt, timeout_sec=float(timeout_sec))
            elapsed = result.response_time_ms or int((time.perf_counter() - t0) * 1000)

            if result.error or not result.text:
                err = result.error or "empty response"
                await _handle_failure(
                    endpoint,
                    err,
                    request_time=request_time,
                    response_time_ms=elapsed,
                    pool=pool,
                    cooldown=cooldown,
                    cfg_cooldown_ms=cfg.cooldown_ms,
                    rate_limited=is_quota_error(Exception(err)),
                )
                last_error = err
                await asyncio.sleep(cfg.retry_delay_ms / 1000.0)
                continue

            pool.record_success(endpoint, response_time_ms=elapsed)
            cooldown.clear(endpoint.provider, endpoint.key_index)
            _log_request(
                endpoint,
                request_time=request_time,
                response_time_ms=elapsed,
                status=RequestStatus.SUCCESS,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                total_tokens=result.total_tokens,
            )
            logger.info(
                "AI route OK provider=%s key#%s model=%s %dms",
                endpoint.provider.value,
                endpoint.key_index,
                endpoint.model,
                elapsed,
            )
            return result.text

        except AiQuotaError as e:
            elapsed = int((time.perf_counter() - t0) * 1000)
            await _handle_failure(
                endpoint,
                str(e),
                request_time=request_time,
                response_time_ms=elapsed,
                pool=pool,
                cooldown=cooldown,
                cfg_cooldown_ms=cfg.cooldown_ms,
                rate_limited=True,
            )
            last_error = str(e)
            await asyncio.sleep(cfg.retry_delay_ms / 1000.0)
            continue

        except Exception as e:
            elapsed = int((time.perf_counter() - t0) * 1000)
            if not is_failover_error(e):
                _log_request(
                    endpoint,
                    request_time=request_time,
                    response_time_ms=elapsed,
                    status=RequestStatus.ERROR,
                    error=str(e)[:500],
                )
                raise

            await _handle_failure(
                endpoint,
                str(e),
                request_time=request_time,
                response_time_ms=elapsed,
                pool=pool,
                cooldown=cooldown,
                cfg_cooldown_ms=cfg.cooldown_ms,
                rate_limited=is_quota_error(e),
            )
            last_error = str(e)
            await asyncio.sleep(cfg.retry_delay_ms / 1000.0)

    if is_quota_error(Exception(last_error)):
        raise AiQuotaError(last_error)
    raise RuntimeError(last_error)


async def _handle_failure(
    endpoint: Endpoint,
    error: str,
    *,
    request_time: str,
    response_time_ms: int,
    pool,
    cooldown,
    cfg_cooldown_ms: int,
    rate_limited: bool,
) -> None:
    pool.record_failure(endpoint, rate_limited=rate_limited)
    cooldown.set_cooldown(
        endpoint.provider,
        endpoint.key_index,
        duration_ms=cfg_cooldown_ms,
        reason="rate_limit" if rate_limited else "error",
    )
    _log_request(
        endpoint,
        request_time=request_time,
        response_time_ms=response_time_ms,
        status=RequestStatus.FAILOVER,
        error=error[:500],
    )
    logger.warning(
        "AI failover provider=%s key#%s model=%s err=%s",
        endpoint.provider.value,
        endpoint.key_index,
        endpoint.model,
        error[:120],
    )


def _log_request(
    endpoint: Endpoint,
    *,
    request_time: str,
    response_time_ms: int,
    status: RequestStatus,
    error: str | None = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
) -> None:
    try:
        from database.repositories.ai_routing import log_request

        log_request(
            provider=endpoint.provider.value,
            key_index=endpoint.key_index,
            model=endpoint.model,
            request_time=request_time,
            response_time_ms=response_time_ms,
            status=status.value,
            error=error,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )
    except Exception as e:
        logger.debug("ai_request_logs write failed: %s", e)
