"""Probe all configured AI provider keys (admin diagnostics)."""
from __future__ import annotations

import asyncio
import logging
import time

from features.ai.routing.adapters import probe_endpoint
from features.ai.routing.config import load_routing_config
from features.ai.routing.types import Endpoint, ProviderName

logger = logging.getLogger(__name__)

_PROBE_CONCURRENCY = 4


async def _probe_one(
    provider: ProviderName,
    key_index: int,
    api_key: str,
    models: tuple[str, ...],
    extras: dict[str, str],
    *,
    timeout_sec: float,
) -> dict:
    t0 = time.perf_counter()
    last_error = "no_models_configured"
    used_model = models[0] if models else ""
    try:
        for model in models or ("",):
            ep = Endpoint(
                provider=provider,
                key_index=key_index,
                model=model,
                api_key=api_key,
                extras=extras,
            )
            ok, err = await probe_endpoint(ep, timeout_sec=timeout_sec)
            if ok:
                ms = int((time.perf_counter() - t0) * 1000)
                return {
                    "provider": provider.value,
                    "key_index": key_index,
                    "model": model,
                    "ok": True,
                    "latency_ms": ms,
                    "error": None,
                }
            last_error = err or "probe_failed"
            used_model = model
        ms = int((time.perf_counter() - t0) * 1000)
        return {
            "provider": provider.value,
            "key_index": key_index,
            "model": used_model,
            "ok": False,
            "latency_ms": ms,
            "error": last_error,
        }
    except Exception as exc:
        ms = int((time.perf_counter() - t0) * 1000)
        return {
            "provider": provider.value,
            "key_index": key_index,
            "model": used_model,
            "ok": False,
            "latency_ms": ms,
            "error": str(exc)[:200],
        }


async def probe_all_keys(*, timeout_sec: float = 20.0) -> dict:
    """Test each configured API key with a minimal prompt."""
    cfg = load_routing_config()
    tasks: list[asyncio.Task] = []
    sem = asyncio.Semaphore(_PROBE_CONCURRENCY)

    async def run(
        prov: ProviderName,
        ki: int,
        key: str,
        models: tuple[str, ...],
        extras: dict[str, str],
    ) -> dict:
        async with sem:
            return await _probe_one(prov, ki, key, models, extras, timeout_sec=timeout_sec)

    summary: dict[str, dict] = {}
    for pname in ProviderName:
        pcfg = cfg.providers.get(pname)
        if not pcfg:
            summary[pname.value] = {
                "provider": pname.value,
                "key_count": 0,
                "ok": 0,
                "fail": 0,
                "configured": False,
            }
            continue
        n = len(pcfg.api_keys)
        summary[pname.value] = {
            "provider": pname.value,
            "key_count": n,
            "ok": 0,
            "fail": 0,
            "configured": n > 0,
            "models": list(pcfg.models),
        }
        if not n:
            continue
        models = tuple(pcfg.models)
        extras = dict(pcfg.extras)
        for i, api_key in enumerate(pcfg.api_keys):
            tasks.append(asyncio.create_task(run(pname, i + 1, api_key, models, extras)))

    results: list[dict] = []
    if tasks:
        results = await asyncio.gather(*tasks)

    for row in results:
        prov = row["provider"]
        if row.get("ok"):
            summary[prov]["ok"] += 1
        else:
            summary[prov]["fail"] += 1

    return {
        "primary_provider": cfg.primary_provider.value,
        "fallback_order": [p.value for p in cfg.fallback_order],
        "summary": summary,
        "results": sorted(results, key=lambda r: (r["provider"], r["key_index"])),
        "total_keys": len(results),
        "ok_keys": sum(1 for r in results if r.get("ok")),
        "fail_keys": sum(1 for r in results if not r.get("ok")),
    }


def build_config_summary() -> dict:
    """Non-secret routing config for admin dashboards."""
    cfg = load_routing_config()
    providers: dict[str, dict] = {}
    total_keys = 0
    for pname in ProviderName:
        pcfg = cfg.providers.get(pname)
        n = len(pcfg.api_keys) if pcfg else 0
        total_keys += n
        providers[pname.value] = {
            "key_count": n,
            "configured": n > 0,
            "models": list(pcfg.models) if pcfg else [],
            "primary_model": pcfg.models[0] if pcfg and pcfg.models else "",
            "in_pool": bool(pcfg and pcfg.api_keys),
        }
    return {
        "primary_provider": cfg.primary_provider.value,
        "fallback_order": [p.value for p in cfg.fallback_order],
        "request_timeout_ms": cfg.request_timeout_ms,
        "max_retries": cfg.max_retries,
        "cooldown_ms": cfg.cooldown_ms,
        "total_keys": total_keys,
        "providers": providers,
    }
