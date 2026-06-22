"""Lightweight in-process TTL cache."""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any

_lock = threading.Lock()
_store: OrderedDict[str, tuple[float, Any]] = OrderedDict()
_MAX = 512
_DEFAULT_TTL = 30.0


def get(key: str) -> Any | None:
    now = time.monotonic()
    with _lock:
        hit = _store.get(key)
        if not hit:
            return None
        expires, value = hit
        if now > expires:
            del _store[key]
            return None
        _store.move_to_end(key)
        return value


def set(key: str, value: Any, ttl: float = _DEFAULT_TTL) -> None:
    expires = time.monotonic() + max(1.0, ttl)
    with _lock:
        while len(_store) >= _MAX:
            _store.popitem(last=False)
        _store[key] = (expires, value)
        _store.move_to_end(key)


def invalidate(prefix: str) -> None:
    with _lock:
        for k in list(_store.keys()):
            if k.startswith(prefix):
                del _store[k]
