"""Per-provider API key quota tracking and reset detection."""
from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone

from features.ai.routing.config import load_routing_config
from features.ai.routing.types import ProviderName

logger = logging.getLogger(__name__)

_DEFAULT_DAILY_LIMITS: dict[str, int] = {
    "gemini": 1500,
    "openai": 10_000,
    "openrouter": 5000,
    "groq": 14_400,
    "cloudflare": 10_000,
    "sambanova": 5000,
    "github": 5000,
}


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _daily_limit(provider: str) -> int:
    key = f"AI_QUOTA_DAILY_{provider.upper()}"
    raw = (os.getenv(key) or os.getenv("AI_QUOTA_DAILY_LIMIT") or "").strip()
    try:
        if raw:
            return max(1, int(raw))
    except ValueError:
        pass
    return _DEFAULT_DAILY_LIMITS.get(provider.lower(), 1500)


@dataclass
class QuotaState:
    provider: str
    key_index: int
    model: str = ""
    quota_percent: float = 100.0
    requests_used: int = 0
    requests_remaining: int = 0
    status: str = "ACTIVE"
    last_success: str | None = None
    last_failure: str | None = None
    reset_time: str | None = None
    health_status: str = "HEALTHY"
    daily_limit: int = 1500
    was_exhausted: bool = False

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "key_index": self.key_index,
            "model": self.model,
            "quota_percent": round(self.quota_percent, 1),
            "requests_used": self.requests_used,
            "requests_remaining": self.requests_remaining,
            "requests_remaining_pct": round(self.quota_percent, 1),
            "status": self.status,
            "last_success": self.last_success,
            "last_failure": self.last_failure,
            "reset_time": self.reset_time,
            "health_status": self.health_status,
            "daily_limit": self.daily_limit,
        }


class QuotaMonitor:
    """Tracks estimated quota per provider key; detects quota refresh after exhaustion."""

    def __init__(self) -> None:
        self._states: dict[tuple[str, int], QuotaState] = {}
        self._lock = threading.RLock()
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            if os.getenv("_HUJJATCHI_TEST", "").strip() != "1":
                try:
                    from database.repositories.ai_quota import load_all_states

                    for row in load_all_states():
                        prov = str(row.get("provider") or "")
                        ki = int(row.get("key_index") or 0)
                        if not prov or ki < 1:
                            continue
                        st = QuotaState(
                            provider=prov,
                            key_index=ki,
                            model=str(row.get("model") or ""),
                            quota_percent=float(row.get("quota_percent") or 100),
                            requests_used=int(row.get("requests_used") or 0),
                            requests_remaining=int(row.get("requests_remaining") or 0),
                            status=str(row.get("status") or "ACTIVE"),
                            last_success=row.get("last_success"),
                            last_failure=row.get("last_failure"),
                            reset_time=row.get("reset_time"),
                            health_status=str(row.get("health_status") or "HEALTHY"),
                            daily_limit=int(row.get("daily_limit") or _daily_limit(prov)),
                            was_exhausted=str(row.get("status") or "").upper() == "EXHAUSTED",
                        )
                        self._states[(prov, ki)] = st
                except Exception as e:
                    logger.debug("Quota state load skipped: %s", e)
            self._init_from_config()
            self._loaded = True

    def _init_from_config(self) -> None:
        cfg = load_routing_config()
        for pname, pcfg in cfg.providers.items():
            for i in range(len(pcfg.api_keys)):
                ki = i + 1
                key = (pname.value, ki)
                if key not in self._states:
                    limit = _daily_limit(pname.value)
                    self._states[key] = QuotaState(
                        provider=pname.value,
                        key_index=ki,
                        model=pcfg.models[0] if pcfg.models else "",
                        requests_remaining=limit,
                        daily_limit=limit,
                    )

    def _get(self, provider: str, key_index: int) -> QuotaState:
        self._ensure_loaded()
        key = (provider, key_index)
        if key not in self._states:
            limit = _daily_limit(provider)
            self._states[key] = QuotaState(
                provider=provider,
                key_index=key_index,
                requests_remaining=limit,
                daily_limit=limit,
            )
        return self._states[key]

    def _recalc(self, state: QuotaState) -> None:
        limit = max(1, state.daily_limit)
        used = max(0, state.requests_used)
        remaining = max(0, limit - used)
        state.requests_remaining = remaining
        state.quota_percent = round(max(0.0, min(100.0, (remaining / limit) * 100.0)), 1)

    def _persist(self, state: QuotaState, *, event_type: str = "snapshot") -> None:
        if os.getenv("_HUJJATCHI_TEST", "").strip() == "1":
            return
        try:
            from database.repositories.ai_quota import insert_history, upsert_state

            upsert_state(
                provider=state.provider,
                key_index=state.key_index,
                model=state.model or None,
                quota_percent=state.quota_percent,
                requests_used=state.requests_used,
                requests_remaining=state.requests_remaining,
                status=state.status,
                last_success=state.last_success,
                last_failure=state.last_failure,
                reset_time=state.reset_time,
                health_status=state.health_status,
                daily_limit=state.daily_limit,
            )
            # Periodic "snapshot" must NOT inflate ai_quota_history (was 700k+ rows
            # and made PRAGMA integrity_check / health probes multi-second).
            if event_type != "snapshot":
                insert_history(
                    provider=state.provider,
                    key_index=state.key_index,
                    quota_percent=state.quota_percent,
                    requests_used=state.requests_used,
                    requests_remaining=state.requests_remaining,
                    status=state.status,
                    event_type=event_type,
                )
        except Exception as e:
            logger.debug("Quota persist failed: %s", e)

    def _log_quota_reset(self, state: QuotaState) -> None:
        now = _utc_iso()
        logger.info(
            "[%s] %s Key #%s quota refreshed. Usage: 0 Remaining: 100%% Status: ACTIVE",
            now[:10],
            state.provider.capitalize(),
            state.key_index,
        )
        state.requests_used = 0
        state.requests_remaining = state.daily_limit
        state.quota_percent = 100.0
        state.status = "ACTIVE"
        state.health_status = "HEALTHY"
        state.reset_time = now
        state.was_exhausted = False
        self._persist(state, event_type="quota_reset")

    def record_success(self, provider: str, key_index: int, model: str) -> None:
        with self._lock:
            state = self._get(provider, key_index)
            if state.was_exhausted or state.status in ("EXHAUSTED", "COOLDOWN"):
                self._log_quota_reset(state)
            state.model = model or state.model
            state.requests_used += 1
            state.last_success = _utc_iso()
            state.status = "ACTIVE"
            state.health_status = "HEALTHY"
            state.was_exhausted = False
            self._recalc(state)
            self._persist(state, event_type="success")

    def record_quota_exhausted(self, provider: str, key_index: int, model: str) -> None:
        with self._lock:
            state = self._get(provider, key_index)
            state.model = model or state.model
            state.requests_used = state.daily_limit
            state.last_failure = _utc_iso()
            state.status = "EXHAUSTED"
            state.health_status = "QUOTA_EXCEEDED"
            state.was_exhausted = True
            state.quota_percent = 0.0
            state.requests_remaining = 0
            self._persist(state, event_type="quota_exhausted")

    def record_failure(self, provider: str, key_index: int, model: str, *, rate_limited: bool) -> None:
        if rate_limited:
            self.record_quota_exhausted(provider, key_index, model)
            return
        with self._lock:
            state = self._get(provider, key_index)
            state.model = model or state.model
            state.requests_used += 1
            state.last_failure = _utc_iso()
            if state.status != "EXHAUSTED":
                state.status = "DEGRADED"
                state.health_status = "DEGRADED"
            self._recalc(state)
            self._persist(state, event_type="failure")

    def mark_cooldown(self, provider: str, key_index: int) -> None:
        with self._lock:
            state = self._get(provider, key_index)
            if state.status != "EXHAUSTED":
                state.status = "COOLDOWN"
                state.health_status = "COOLDOWN"
                self._persist(state, event_type="cooldown")

    def snapshot_all(self) -> list[dict]:
        """Periodic snapshot — persists all keys without incrementing counters."""
        self._ensure_loaded()
        out: list[dict] = []
        with self._lock:
            for state in self._states.values():
                self._recalc(state)
                self._persist(state, event_type="snapshot")
                out.append(state.to_dict())
        return sorted(out, key=lambda x: (x["provider"], x["key_index"]))

    def list_all(self) -> list[dict]:
        self._ensure_loaded()
        try:
            from features.ai.routing.cooldown import get_cooldown_registry
            from features.ai.routing.config import load_routing_config

            cooldown = get_cooldown_registry(load_routing_config().cooldown_ms)
        except Exception:
            cooldown = None

        with self._lock:
            rows = []
            for state in sorted(self._states.values(), key=lambda s: (s.provider, s.key_index)):
                if cooldown and cooldown.is_cooling(
                    ProviderName(state.provider), state.key_index
                ):
                    if state.status != "EXHAUSTED":
                        state.status = "COOLDOWN"
                        state.health_status = "COOLDOWN"
                if state.status != "EXHAUSTED":
                    self._recalc(state)
                rows.append(state.to_dict())
            return rows


_monitor: QuotaMonitor | None = None
_monitor_lock = threading.Lock()


def get_quota_monitor() -> QuotaMonitor:
    global _monitor
    with _monitor_lock:
        if _monitor is None:
            _monitor = QuotaMonitor()
        return _monitor


def reset_quota_monitor() -> QuotaMonitor:
    global _monitor
    with _monitor_lock:
        _monitor = QuotaMonitor()
        return _monitor
