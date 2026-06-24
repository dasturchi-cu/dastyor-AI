"""Hozirgi ish (h.v.) — ajratish va namunadagi sana qatori."""
from __future__ import annotations

import re
from typing import Any

_PRESENT_TOKENS = (
    "hv",
    "hvgacha",
    "hozirgacha",
    "ҳв",
    "ҳвгача",
    "ҳозиргача",
    "present",
    "current",
)

_PRESENT_RE = re.compile(
    r"h\.?\s*v\.?|ҳ\.?\s*в|hozirgacha|ҳозиргача|present|current",
    re.IGNORECASE,
)


def is_present_year_token(value: str) -> bool:
    norm = re.sub(r"[\s.\-_/]", "", (value or "").lower())
    return any(tok in norm for tok in _PRESENT_TOKENS)


def format_current_job_year(year_raw: str, lang: str = "uz_lat") -> str:
    """Masalan: 2014 → '2014-yildan:' yoki '2014 йилдан:'."""
    raw = (year_raw or "").strip().rstrip(":")
    if not raw:
        return ""
    if re.search(r"(yildan|йилдан|oktabr|октябр|yanvar|январ)", raw, re.IGNORECASE):
        return raw if raw.endswith(":") else f"{raw}:"
    match = re.search(r"(19|20)\d{2}", raw)
    year = match.group(0) if match else raw.rstrip(".")
    if (lang or "uz_lat") == "uz_cyr":
        return f"{year} йилдан:"
    return f"{year}-yildan:"


def _work_year_raw(item: dict[str, Any]) -> str:
    year = str(item.get("year") or item.get("years") or item.get("from") or "").strip()
    if not year and (item.get("f") or item.get("t")):
        f = str(item.get("f") or "").strip()
        t = str(item.get("t") or "").strip()
        year = f"{f}-{t}".strip("-") if f or t else ""
    return year


def _work_position(item: dict[str, Any]) -> str:
    return str(
        item.get("position")
        or item.get("desc")
        or item.get("description")
        or item.get("job")
        or item.get("d")
        or ""
    ).strip()


def extract_current_job(
    work_items: list[dict[str, Any]],
    *,
    current_job: str = "",
    current_job_year: str = "",
    lang: str = "uz_lat",
) -> tuple[str, str, list[dict[str, Any]]]:
    """H.v. ishni ajratib, qolgan mehnat tarixini qaytaradi."""
    job = (current_job or "").strip()
    year = (current_job_year or "").strip()
    items = [dict(x) for x in work_items]

    if not job:
        for idx, item in enumerate(items):
            year_raw = _work_year_raw(item)
            pos = _work_position(item)
            if not pos:
                continue
            if is_present_year_token(year_raw) or _PRESENT_RE.search(year_raw):
                start = str(item.get("from") or item.get("f") or "").strip()
                if not start:
                    m = re.search(r"(19|20)\d{2}", year_raw)
                    start = m.group(0) if m else year_raw
                items.pop(idx)
                job = pos
                year = start
                break

    if job:
        year = format_current_job_year(year, lang)
        filtered: list[dict[str, Any]] = []
        for item in items:
            year_raw = _work_year_raw(item)
            pos = _work_position(item)
            if pos and job == pos and (
                is_present_year_token(year_raw) or _PRESENT_RE.search(year_raw)
            ):
                continue
            filtered.append(item)
        items = filtered

    return job, year, items
