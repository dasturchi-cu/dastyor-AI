"""Provider/key cooldown tracking."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from features.ai.routing.types import ProviderName


def _utc_iso(ts: float | None = None) -> str:
    t = ts if ts is not None else time.time()
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class CooldownEntry:
    provider: ProviderName
    key_index: int
    until_ts: float
    reason: str = ""

    @property
    def in_cooldown(self) -> bool:
        return time.time() < self.until_ts

    @property
    def until_iso(self) -> str:
        return _utc_iso(self.until_ts)


class CooldownRegistry:
    """Thread-safe cooldown registry for (provider, key_index) pairs."""

    def __init__(self, default_cooldown_ms: int = 900_000) -> None:
        self._default_ms = max(1, default_cooldown_ms)
        self._entries: dict[tuple[str, int], CooldownEntry] = {}
        self._lock = threading.Lock()

    def set_cooldown(
        self,
        provider: ProviderName,
        key_index: int,
        *,
        duration_ms: int | None = None,
        reason: str = "",
    ) -> CooldownEntry:
        ms = duration_ms if duration_ms is not None else self._default_ms
        until = time.time() + ms / 1000.0
        entry = CooldownEntry(provider=provider, key_index=key_index, until_ts=until, reason=reason)
        with self._lock:
            self._entries[(provider.value, key_index)] = entry
        return entry

    def is_cooling(self, provider: ProviderName, key_index: int) -> bool:
        with self._lock:
            entry = self._entries.get((provider.value, key_index))
            if not entry:
                return False
            if not entry.in_cooldown:
                del self._entries[(provider.value, key_index)]
                return False
            return True

    def clear(self, provider: ProviderName, key_index: int) -> None:
        with self._lock:
            self._entries.pop((provider.value, key_index), None)

    def list_active(self) -> list[dict]:
        now = time.time()
        out: list[dict] = []
        with self._lock:
            stale: list[tuple[str, int]] = []
            for key, entry in self._entries.items():
                if entry.until_ts <= now:
                    stale.append(key)
                    continue
                out.append(
                    {
                        "provider": entry.provider.value,
                        "key_index": entry.key_index,
                        "until": entry.until_iso,
                        "reason": entry.reason,
                        "remaining_sec": int(entry.until_ts - now),
                    }
                )
            for key in stale:
                del self._entries[key]
        return sorted(out, key=lambda x: (x["provider"], x["key_index"]))


_registry: CooldownRegistry | None = None
_registry_lock = threading.Lock()


def get_cooldown_registry(default_ms: int = 900_000) -> CooldownRegistry:
    global _registry
    with _registry_lock:
        if _registry is None:
            _registry = CooldownRegistry(default_cooldown_ms=default_ms)
        return _registry
