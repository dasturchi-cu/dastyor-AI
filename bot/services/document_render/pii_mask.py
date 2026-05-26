"""Mask sensitive personal data in preview documents without breaking layout."""

from __future__ import annotations

import re
from typing import Any

# Uzbek phone patterns (+998, 998, local 9-digit groups)
_PHONE = re.compile(
    r"(?<!\d)(?:\+?998[\s\-()]?\d{2}[\s\-()]?\d{3}[\s\-()]?\d{2}[\s\-()]?\d{2}|"
    r"\+?\d{1,3}[\s\-()]?\d{2,3}[\s\-()]?\d{3}[\s\-()]?\d{2}[\s\-()]?\d{2})(?!\d)"
)
_PINFL = re.compile(r"\b(\d{14})\b")
_PASSPORT = re.compile(r"\b([A-Za-zА-Яа-я]{2}\d{7})\b")
_JSHSHIR = re.compile(r"\b(JSHSHIR|ЖШШИР|PINFL|ПИНФЛ)[\s:]*(\d{14})\b", re.I)


def _mask_digits_partial(digits: str, *, keep_start: int = 2, keep_end: int = 2) -> str:
    if len(digits) <= keep_start + keep_end:
        return "*" * len(digits)
    mid = max(1, len(digits) - keep_start - keep_end)
    return digits[:keep_start] + ("*" * mid) + digits[-keep_end:]


def _mask_phone_match(m: re.Match[str]) -> str:
    raw = m.group(0)
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 7:
        return raw
    masked = _mask_digits_partial(digits, keep_start=3, keep_end=2)
    # Preserve leading + if present
    prefix = "+" if raw.strip().startswith("+") else ""
    return f'<span class="pii-blur">{prefix}{masked}</span>'


def _mask_passport_match(m: re.Match[str]) -> str:
    val = m.group(1)
    letters = val[:2]
    nums = val[2:]
    masked = letters + _mask_digits_partial(nums, keep_start=0, keep_end=2)
    return f'<span class="pii-partial">{masked}</span>'


def _mask_pinfl_match(m: re.Match[str]) -> str:
    digits = m.group(1)
    masked = _mask_digits_partial(digits, keep_start=2, keep_end=2)
    return f'<span class="pii-partial">{masked}</span>'


def _mask_jshshir_match(m: re.Match[str]) -> str:
    label = m.group(1)
    digits = m.group(2)
    masked = _mask_digits_partial(digits, keep_start=2, keep_end=2)
    return f'{label}: <span class="pii-partial">{masked}</span>'


def mask_text_for_preview(text: Any) -> str:
    """Return HTML-safe text with phone blur and ID partial masks."""
    s = "" if text is None else str(text)
    if not s.strip():
        return s

    out = _JSHSHIR.sub(_mask_jshshir_match, s)
    out = _PINFL.sub(_mask_pinfl_match, out)
    out = _PASSPORT.sub(_mask_passport_match, out)
    out = _PHONE.sub(_mask_phone_match, out)
    return out


def mask_relatives_for_preview(relatives: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for rel in relatives or []:
        if not isinstance(rel, dict):
            continue
        item = dict(rel)
        for key in ("fullname", "name", "birth_year_place", "birth", "work_place", "job", "address", "addr"):
            if key in item and item[key]:
                item[key] = mask_text_for_preview(item[key])
        out.append(item)
    return out
