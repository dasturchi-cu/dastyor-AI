"""Obyektivka — bitta manba: ish tajribasi (preview, DOCX, PDF)."""
from __future__ import annotations

import json
import re
from typing import Any

from features.obyektivka.none_values import is_none_token

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


_WORK_LIST_KEYS = (
    "work_experience",
    "works",
    "employment_history",
    "employmentHistory",
    "work_history",
    "workHistory",
)


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _parse_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [x for x in value if isinstance(x, dict)]
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def _parse_work_list(raw: dict[str, Any]) -> list[dict[str, Any]]:
    for key in _WORK_LIST_KEYS:
        items = _parse_list(raw.get(key))
        if items:
            return items
    return []


def _parse_year_range(year: str) -> tuple[str, str]:
    yr = (year or "").strip()
    if not yr:
        return "", ""
    if is_present_year_token(yr) or _PRESENT_RE.search(yr):
        m = re.search(r"(19|20)\d{2}", yr)
        return (m.group(0) if m else ""), "h.v"
    m = re.match(r"^(\d{4})\s*[-–—]\s*(.+)$", yr)
    if m:
        tail = m.group(2).strip().rstrip(".")
        if is_present_year_token(tail) or _PRESENT_RE.search(tail):
            return m.group(1), "h.v"
        ey = re.match(r"^(\d{4})", tail)
        return m.group(1), (ey.group(1) if ey else tail.replace("yy.", "").replace("йй.", "").strip())
    m = re.search(r"^(19|20)\d{2}", yr)
    if m:
        return m.group(0), ""
    return yr, ""


def _canonical_work_item(item: dict[str, Any]) -> dict[str, Any]:
    f = _to_text(item.get("from") or item.get("f"))
    t = _to_text(item.get("to") or item.get("t"))
    pos = _to_text(
        item.get("position")
        or item.get("desc")
        or item.get("description")
        or item.get("job")
        or item.get("d")
    )
    year = _to_text(item.get("year") or item.get("years") or item.get("period"))

    if f or t:
        from_y, to_y = f, t
    elif year:
        from_y, to_y = _parse_year_range(year)
    else:
        from_y, to_y = "", ""

    is_current = bool(
        is_present_year_token(to_y)
        or is_present_year_token(year)
        or (year and _PRESENT_RE.search(year))
    )
    if is_current:
        to_y = "h.v"

    return {
        "from_year": from_y,
        "to_year": to_y,
        "position": pos,
        "is_current": is_current,
    }


def _work_position(item: dict[str, Any]) -> str:
    if "position" in item:
        return _to_text(item.get("position"))
    return _to_text(item.get("desc") or item.get("description") or item.get("job") or item.get("d"))


def _meaningful_position(item: dict[str, Any]) -> bool:
    pos = _to_text(item.get("position"))
    return bool(pos) and not is_none_token(pos)


def _resolve_current_display(
    items: list[dict[str, Any]],
    *,
    current_job: str = "",
    current_job_year: str = "",
    lang: str = "uz_lat",
) -> tuple[str, str]:
    job = (current_job or "").strip()
    year = (current_job_year or "").strip()
    if is_none_token(job):
        job = ""
        year = ""

    if not job:
        for item in items:
            pos = item.get("position") or ""
            if not _meaningful_position(item):
                continue
            if item.get("is_current") or is_present_year_token(item.get("to_year") or ""):
                job = pos
                year = item.get("from_year") or year
                break

    if job:
        year = format_current_job_year(year, lang)
    else:
        year = ""
    return job, year


def _mehnat_year_prefix(item: dict[str, Any], lang: str) -> str:
    f = _to_text(item.get("from_year"))
    t = _to_text(item.get("to_year"))
    cyr = (lang or "uz_lat") == "uz_cyr"
    hv = "ҳ.в." if cyr else "h.v."
    y_mark = "й." if cyr else "y."
    yy_mark = "йй." if cyr else "yy."

    if item.get("is_current") or is_present_year_token(t):
        return f"{f} {y_mark} - {hv}" if f else hv

    if f and t and t not in ("h.v", "hv"):
        core = f"{f}-{t}"
        if "yy" not in core.lower() and "йй" not in core:
            return f"{core} {yy_mark}"
        return core
    if f:
        if "yy" not in f.lower() and "йй" not in f:
            return f"{f} {yy_mark}"
        return f
    return ""


def format_mehnat_line(item: dict[str, Any], lang: str = "uz_lat") -> str:
    prefix = _mehnat_year_prefix(item, lang)
    pos = _to_text(item.get("position"))
    if prefix and pos:
        return f"{prefix} - {pos}"
    return prefix or pos


def _to_render_work_item(item: dict[str, Any], lang: str) -> dict[str, str]:
    return {
        "year": _mehnat_year_prefix(item, lang),
        "position": _to_text(item.get("position")),
    }


def _ensure_current_in_list(
    items: list[dict[str, Any]],
    job: str,
    year: str,
) -> list[dict[str, Any]]:
    if not job:
        return items
    for item in items:
        if _to_text(item.get("position")) == job and (
            item.get("is_current") or is_present_year_token(item.get("to_year") or "")
        ):
            return items
    m = re.search(r"(19|20)\d{2}", year or "")
    from_y = m.group(0) if m else ""
    return items + [
        {
            "from_year": from_y,
            "to_year": "h.v",
            "position": job,
            "is_current": True,
        }
    ]


def build_malumotnoma_data(raw: dict[str, Any]) -> dict[str, Any]:
    """
  Form / DB / API → bitta normalizatsiya.
  H.v. ish tepada ham, MEHNAT FAOLIYATI da ham qoladi.
  """
    lang = _to_text(raw.get("lang")) or "uz_lat"
    explicit_job = _to_text(
        raw.get("current_job") or raw.get("currentJob") or raw.get("current_position") or raw.get("current_employment")
    )
    explicit_year = _to_text(raw.get("current_job_year") or raw.get("currentJobYear"))
    if is_none_token(explicit_job):
        explicit_job = ""
        explicit_year = ""

    items = [_canonical_work_item(w) for w in _parse_work_list(raw)]
    items = [x for x in items if _meaningful_position(x)]

    current_job, current_job_year = _resolve_current_display(
        items,
        current_job=explicit_job,
        current_job_year=explicit_year,
        lang=lang,
    )
    items = _ensure_current_in_list(items, current_job, current_job_year)

    work_experience = [_to_render_work_item(x, lang) for x in items]
    work_lines = [line for x in items if (line := format_mehnat_line(x, lang))]

    return {
        "lang": lang,
        "current_job": current_job,
        "current_job_year": current_job_year,
        "work_experience": work_experience,
        "work_lines": work_lines,
    }
