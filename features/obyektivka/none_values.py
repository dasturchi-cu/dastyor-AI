"""Bo'sh maydon: yo'q / йўқ — til bo'yicha bir xil."""
from __future__ import annotations

import re

NONE_UZ = "yo'q"
NONE_CYR = "йўқ"

_NONE_COMPACT = frozenset(
    {
        "yoq",
        "yok",
        "йўқ",
        "йок",
        "йўк",
        "no",
        "none",
        "йўқ",
    }
)


def _compact(value: str) -> str:
    v = (value or "").strip().lower()
    v = v.replace("ʻ", "'").replace("'", "'")
    return re.sub(r"[\s''\-_.]", "", v)


def is_none_token(value: str) -> bool:
    if not (value or "").strip():
        return True
    return _compact(value) in _NONE_COMPACT


def none_for_lang(lang: str) -> str:
    key = (lang or "uz_lat").strip().lower()
    if key == "en":
        return "none"
    if key == "ru":
        return "нет"
    return NONE_CYR if key == "uz_cyr" else NONE_UZ


def field_or_none(value: str, lang: str = "uz_lat") -> str:
    """Formadagi yo'q/йўқ → joriy til uchun to'g'ri «yo'q» yoki «йўқ»."""
    from features.ai.gemini_client import is_ai_garbage

    if is_ai_garbage(value):
        return none_for_lang(lang)
    if is_none_token(value):
        return none_for_lang(lang)
    return (value or "").strip()


def field_for_display(value: str, lang: str = "uz_lat", *, preview: bool = False) -> str:
    """Preview/demo: bo'sh yoki yo'q → ''; pullik hujjat: yo'q/йўқ."""
    if is_none_token(value):
        return "" if preview else none_for_lang(lang)
    return (value or "").strip()
