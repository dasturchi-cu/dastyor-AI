"""Endpoint pool with round-robin, health-weighted rotation."""
from __future__ import annotations

import itertools
import threading
import time
from dataclasses import dataclass, field

from features.ai.routing.config import load_routing_config
from features.ai.routing.cooldown import get_cooldown_registry
from features.ai.routing.types import ActiveRoute, Endpoint, ProviderName, RoutingConfig


def _utc_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class HealthRecord:
    successes: int = 0
    failures: int = 0
    rate_limits: int = 0
    last_success_ts: float = 0.0
    last_failure_ts: float = 0.0

    @property
    def total(self) -> int:
        return self.successes + self.failures

    @property
    def score(self) -> float:
        if self.total == 0:
            return 100.0
        # Penalize rate limits slightly more
        penalty = self.rate_limits * 0.5
        raw = (self.successes / self.total) * 100.0 - penalty
        return max(5.0, min(100.0, raw))


class EndpointPool:
    """
    Builds ordered endpoint list per request using:
    - provider order (primary → fallbacks)
    - round-robin key start per provider
    - health-weighted sorting within provider
    - cooldown exclusion
    """

    def __init__(self, config: RoutingConfig | None = None) -> None:
        self._config = config or load_routing_config()
        self._rr_counters: dict[str, itertools.count] = {
            p.value: itertools.count(0) for p in ProviderName
        }
        self._health: dict[tuple[str, int, str], HealthRecord] = {}
        self._lock = threading.Lock()
        self._active = ActiveRoute(
            provider=self._config.primary_provider,
            key_index=1,
            model=self._config.providers.get(self._config.primary_provider, None)
            and self._config.providers[self._config.primary_provider].models[0]
            or "",
            status="IDLE",
            health_pct=100.0,
            updated_at=_utc_iso(),
        )
        self._cooldown = get_cooldown_registry(self._config.cooldown_ms)

    def record_success(self, endpoint: Endpoint, response_time_ms: int = 0) -> None:
        key = (endpoint.provider.value, endpoint.key_index, endpoint.model)
        with self._lock:
            rec = self._health.setdefault(key, HealthRecord())
            rec.successes += 1
            rec.last_success_ts = time.time()
            self._active = ActiveRoute(
                provider=endpoint.provider,
                key_index=endpoint.key_index,
                model=endpoint.model,
                status="ACTIVE",
                health_pct=rec.score,
                updated_at=_utc_iso(),
            )

    def record_failure(
        self,
        endpoint: Endpoint,
        *,
        rate_limited: bool = False,
    ) -> None:
        key = (endpoint.provider.value, endpoint.key_index, endpoint.model)
        with self._lock:
            rec = self._health.setdefault(key, HealthRecord())
            rec.failures += 1
            if rate_limited:
                rec.rate_limits += 1
            rec.last_failure_ts = time.time()

    def get_active_route(self) -> ActiveRoute:
        with self._lock:
            return self._active

    def _health_for(self, provider: ProviderName, key_index: int, model: str) -> float:
        rec = self._health.get((provider.value, key_index, model))
        return rec.score if rec else 100.0

    def _build_provider_endpoints(self, provider: ProviderName) -> list[Endpoint]:
        cfg = self._config.providers.get(provider)
        if not cfg or not cfg.api_keys:
            return []

        n_keys = len(cfg.api_keys)
        start = next(self._rr_counters[provider.value]) % n_keys

        # Round-robin key order: start, start+1, ...
        key_order = [(start + i) % n_keys for i in range(n_keys)]

        endpoints: list[Endpoint] = []
        for ki in key_order:
            key_index = ki + 1  # 1-based display
            if self._cooldown.is_cooling(provider, key_index):
                continue
            api_key = cfg.api_keys[ki]
            for model in cfg.models:
                score = self._health_for(provider, key_index, model)
                weight = score / 100.0
                endpoints.append(
                    Endpoint(
                        provider=provider,
                        key_index=key_index,
                        model=model,
                        api_key=api_key,
                        extras=dict(cfg.extras),
                        health_score=score,
                        weight=max(0.05, weight),
                    )
                )

        # Health-weighted: higher health first, preserve key round-robin groups
        endpoints.sort(key=lambda e: (-e.health_score, e.key_index, e.model))
        return endpoints

    def iter_failover_chain(
        self,
        *,
        preferred_models: list[str] | None = None,
    ) -> list[Endpoint]:
        """Full failover chain for one request."""
        order: list[ProviderName] = [self._config.primary_provider]
        for p in self._config.fallback_order:
            if p not in order:
                order.append(p)

        chain: list[Endpoint] = []
        for provider in order:
            eps = self._build_provider_endpoints(provider)
            if preferred_models and provider == ProviderName.GEMINI:
                eps = self._reorder_models(eps, preferred_models)
            chain.extend(eps)
        return chain

    @staticmethod
    def _reorder_models(endpoints: list[Endpoint], preferred: list[str]) -> list[Endpoint]:
        pref_index = {m: i for i, m in enumerate(preferred)}
        grouped: dict[tuple[str, int], list[Endpoint]] = {}
        for ep in endpoints:
            grouped.setdefault((ep.provider.value, ep.key_index), []).append(ep)

        out: list[Endpoint] = []
        for key in sorted(grouped.keys(), key=lambda k: k[1]):
            group = grouped[key]
            group.sort(
                key=lambda e: (
                    pref_index.get(e.model, len(preferred) + 1),
                    e.model,
                )
            )
            out.extend(group)
        return out

    def snapshot_health(self) -> dict[tuple[str, int, str], HealthRecord]:
        with self._lock:
            return dict(self._health)


_pool: EndpointPool | None = None
_pool_lock = threading.Lock()


def get_endpoint_pool() -> EndpointPool:
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = EndpointPool()
        return _pool


def reset_endpoint_pool() -> EndpointPool:
    global _pool
    with _pool_lock:
        _pool = EndpointPool(load_routing_config())
        return _pool
