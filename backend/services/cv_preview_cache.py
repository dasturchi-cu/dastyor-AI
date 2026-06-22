"""In-memory TTL cache for CV HTML preview (takroriy so‘rovlar va bir xil holat)."""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections import OrderedDict

_MAX = max(32, int(os.getenv("CV_PREVIEW_CACHE_MAX", "384") or "384"))
_TTL = float(os.getenv("CV_PREVIEW_CACHE_TTL_SECONDS", "90") or "90")
# cv_template.html o‘zgarganda eski HTML keshdan bermaslik (jonli ko‘rinish yangilanishi uchun)
_TEMPLATE_REV = (os.getenv("CV_PREVIEW_TEMPLATE_REVISION", "20250403-cv-ico") or "1").strip()

_lock = threading.Lock()
_store: OrderedDict[str, tuple[float, str]] = OrderedDict()


def cache_key_for_cv_preview(data: dict) -> str:
    blob = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    raw = f"{blob}|{_TEMPLATE_REV}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def cv_preview_cache_get(key: str) -> str | None:
    now = time.monotonic()
    with _lock:
        hit = _store.get(key)
        if not hit:
            return None
        ts, html = hit
        if now - ts > _TTL:
            del _store[key]
            return None
        _store.move_to_end(key)
        return html


def cv_preview_cache_set(key: str, html: str) -> None:
    now = time.monotonic()
    with _lock:
        while len(_store) >= _MAX:
            _store.popitem(last=False)
        _store[key] = (now, html)
        _store.move_to_end(key)
