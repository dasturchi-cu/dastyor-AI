"""In-memory TTL cache for Obyektivka PDF preview."""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections import OrderedDict

_MAX = max(32, int(os.getenv("OBY_PREVIEW_CACHE_MAX", "256") or "256"))
_TTL = float(os.getenv("OBY_PREVIEW_CACHE_TTL_SECONDS", "60") or "60")
_TEMPLATE_REV = (os.getenv("OBY_PREVIEW_TEMPLATE_REVISION", "20260622-template-v1") or "1").strip()

_lock = threading.Lock()
_store: OrderedDict[str, tuple[float, bytes]] = OrderedDict()


def cache_key_for_oby_preview(data: dict) -> str:
    blob = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    raw = f"{blob}|{_TEMPLATE_REV}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def oby_preview_cache_get(key: str) -> bytes | None:
    now = time.monotonic()
    with _lock:
        hit = _store.get(key)
        if not hit:
            return None
        ts, pdf = hit
        if now - ts > _TTL:
            del _store[key]
            return None
        _store.move_to_end(key)
        return pdf


def oby_preview_cache_set(key: str, pdf: bytes) -> None:
    now = time.monotonic()
    with _lock:
        while len(_store) >= _MAX:
            _store.popitem(last=False)
        _store[key] = (now, pdf)
        _store.move_to_end(key)
