"""LRU-ish TTL cache for spellcheck API (reduces duplicate Gemini calls)."""
from __future__ import annotations

import hashlib
import os
import time
from collections import OrderedDict

_CACHE_MAX = int(os.getenv("SPELLCHECK_CACHE_MAX", "256"))
_CACHE_TTL = int(os.getenv("SPELLCHECK_CACHE_TTL_SEC", "600"))
_cache: "OrderedDict[str, tuple[float, str, int]]" = OrderedDict()


def spellcheck_cache_get(key: str) -> tuple[str, int] | None:
    now = time.time()
    cached = _cache.get(key)
    if not cached:
        return None
    ts, corrected, fixes = cached
    if now - ts > _CACHE_TTL:
        try:
            del _cache[key]
        except KeyError:
            pass
        return None
    _cache.move_to_end(key)
    return corrected, int(fixes or 0)


def spellcheck_cache_set(key: str, corrected: str, fixes: int) -> None:
    now = time.time()
    _cache[key] = (now, corrected, int(fixes or 0))
    _cache.move_to_end(key)
    while len(_cache) > _CACHE_MAX:
        _cache.popitem(last=False)


def spellcheck_cache_key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
