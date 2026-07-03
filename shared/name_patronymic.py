"""Patronimik qo'shimchalar: o'g'li / qizi — CV va obyektivka ismlarida."""
from __future__ import annotations

import re

_OGLI_RE = re.compile(
    r"\b(?:"
    r"o[''`ʻʼ]?g[''`ʻʼ]?li"
    r"|oʻgʻli|o'g'li|og'li|oğli"
    r"|ўғли|ўгли|огли|огъли|ўғл|ўгл"
    r")\b",
    re.IGNORECASE,
)

_QIZI_RE = re.compile(
    r"\b(?:qizi|қизи|кизи|qizi)\b",
    re.IGNORECASE,
)

_REPLACEMENTS: dict[str, tuple[tuple[re.Pattern[str], str], ...]] = {
    "uz_en": (
        (_OGLI_RE, "son of"),
        (_QIZI_RE, "daughter of"),
    ),
    "uz_ru": (
        (_OGLI_RE, "угли"),
        (_QIZI_RE, "кизи"),
    ),
}


def translate_patronymic_suffixes(text: str, direction: str) -> str:
    """Ismdagi o'g'li / qizi qo'shimchasini maqsadli tilga almashtiradi."""
    raw = (text or "").strip()
    if not raw or direction not in _REPLACEMENTS:
        return raw
    out = raw
    for pattern, repl in _REPLACEMENTS[direction]:
        out = pattern.sub(repl, out)
    return re.sub(r"\s{2,}", " ", out).strip()
