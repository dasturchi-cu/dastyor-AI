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
    return NONE_CYR if (lang or "uz_lat") == "uz_cyr" else NONE_UZ


def field_or_none(value: str, lang: str = "uz_lat") -> str:
    """Formadagi yo'q/йўқ → joriy til uchun to'g'ri «yo'q» yoki «йўқ»."""
    if is_none_token(value):
        return none_for_lang(lang)
    return (value or "").strip()
