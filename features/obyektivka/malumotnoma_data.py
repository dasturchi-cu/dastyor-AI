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


_MONTH_KEYS = (
    "yanvar",
    "fevral",
    "mart",
    "aprel",
    "may",
    "iyun",
    "iyul",
    "avgust",
    "sentyabr",
    "oktyabr",
    "oktabr",
    "noyabr",
    "dekabr",
)

_MONTH_LAT = {
    "yanvar": "yanvar",
    "fevral": "fevral",
    "mart": "mart",
    "aprel": "aprel",
    "may": "may",
    "iyun": "iyun",
    "iyul": "iyul",
    "avgust": "avgust",
    "sentyabr": "sentyabr",
    "oktyabr": "oktabr",
    "oktabr": "oktabr",
    "noyabr": "noyabr",
    "dekabr": "dekabr",
}

_MONTH_CYR = {
    "yanvar": "январ",
    "fevral": "феврал",
    "mart": "март",
    "aprel": "апрел",
    "may": "май",
    "iyun": "июн",
    "iyul": "июл",
    "avgust": "август",
    "sentyabr": "сентябр",
    "oktyabr": "октябр",
    "oktabr": "октябр",
    "noyabr": "ноябр",
    "dekabr": "декабр",
}

_MONTH_EN = {
    "yanvar": "January",
    "fevral": "February",
    "mart": "March",
    "aprel": "April",
    "may": "May",
    "iyun": "June",
    "iyul": "July",
    "avgust": "August",
    "sentyabr": "September",
    "oktyabr": "October",
    "oktabr": "October",
    "noyabr": "November",
    "dekabr": "December",
}

_MONTH_RU = {
    "yanvar": "января",
    "fevral": "февраля",
    "mart": "марта",
    "aprel": "апреля",
    "may": "мая",
    "iyun": "июня",
    "iyul": "июля",
    "avgust": "августа",
    "sentyabr": "сентября",
    "oktyabr": "октября",
    "oktabr": "октября",
    "noyabr": "ноября",
    "dekabr": "декабря",
}


def _month_key_from_text(text: str) -> str:
    low = (text or "").lower()
    for key in _MONTH_KEYS:
        if key in low:
            return key
        cyr = _MONTH_CYR.get(key, "")
        if cyr and cyr in low:
            return key
    return ""


def _parse_since_detail(text: str, year: str = "") -> tuple[str, str]:
    raw = (text or "").strip()
    if not raw:
        return "", ""
    if year:
        raw = re.sub(re.escape(year), "", raw).strip(" -–—.,:")
    day_m = re.search(r"(\d{1,2})(?=\D|$)", raw) or re.search(r"^(\d{1,2})", raw)
    day = day_m.group(1) if day_m else ""
    month = _month_key_from_text(raw)
    return day, month


def _already_formatted_job_year(text: str) -> bool:
    raw = (text or "").strip().rstrip(":")
    if not raw:
        return False
    if re.search(r"(yildan|йилдан|since|года)", raw, re.IGNORECASE):
        return True
    return bool(re.search(r"\d{1,2}\s+\S+\s*(dan|дан)\s*:?$", raw, re.IGNORECASE))


def format_current_job_year(
    year_raw: str,
    lang: str = "uz_lat",
    *,
    since: str = "",
) -> str:
    """Masalan: 2014 → '2014-yildan:'; 2007 + 5 oktabr → '2007 yil 5 oktabrdan:'."""
    raw = (year_raw or "").strip().rstrip(":")
    since = (since or "").strip()
    combined = f"{raw} {since}".strip()
    if _already_formatted_job_year(raw) or _already_formatted_job_year(combined):
        result = raw if _already_formatted_job_year(raw) else combined
        return result if result.endswith(":") else f"{result.rstrip(':')}:"

    year_m = re.search(r"(19|20)\d{2}", raw or since)
    year = year_m.group(0) if year_m else raw.rstrip(".")
    if not year:
        return ""

    day, month_key = _parse_since_detail(since or raw, year)
    lang_clean = (lang or "uz_lat").strip().lower()

    if lang_clean == "en":
        if day and month_key:
            month_disp = _MONTH_EN.get(month_key, month_key)
            return f"Since {month_disp} {day}, {year}:"
        return f"Since {year}:"

    if lang_clean == "ru":
        if day and month_key:
            month_disp = _MONTH_RU.get(month_key, month_key)
            return f"С {day} {month_disp} {year} года:"
        return f"С {year} года:"

    cyr = lang_clean == "uz_cyr"
    if day and month_key:
        month_disp = _MONTH_CYR[month_key] if cyr else _MONTH_LAT[month_key]
        if cyr:
            return f"{year} йил {day} {month_disp}дан:"
        return f"{year} yil {day} {month_disp}dan:"

    if cyr:
        return f"{year} йилдан:"
    return f"{year}-yildan:"


_POSITION_KEYS = (
    "position",
    "desc",
    "description",
    "job",
    "d",
    "work_place",
    "place",
    "company",
    "organization",
    "lavozim",
)

_CURRENT_JOB_KEYS = (
    "current_job",
    "currentJob",
    "current_position",
    "current_employment",
    "currentEmployment",
)

_CURRENT_YEAR_KEYS = ("current_job_year", "currentJobYear")


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


_WORK_LIST_KEYS = (
    "work_experience",
    "works",
    "employment_history",
    "employmentHistory",
    "work_history",
    "workHistory",
)


def _work_position_raw(item: dict[str, Any]) -> str:
    for key in _POSITION_KEYS:
        val = _to_text(item.get(key))
        if val:
            return val
    return ""


def _parse_work_list(raw: dict[str, Any]) -> list[dict[str, Any]]:
    for key in _WORK_LIST_KEYS:
        items = _parse_list(raw.get(key))
        if items:
            return items
    return []


def normalize_obyektivka_raw(raw: dict[str, Any]) -> dict[str, Any]:
    """Form / DB / API aliaslari → bitta canonical payload (preview, DOCX, PDF)."""
    if not isinstance(raw, dict):
        return {}
    out = dict(raw)

    if not _to_text(out.get("current_job")):
        for key in _CURRENT_JOB_KEYS[1:]:
            val = _to_text(out.get(key))
            if val:
                out["current_job"] = val
                break
    if not _to_text(out.get("current_job_year")):
        for key in _CURRENT_YEAR_KEYS[1:]:
            val = _to_text(out.get(key))
            if val:
                out["current_job_year"] = val
                break

    items = _parse_work_list(out)
    if items:
        norm_items: list[dict[str, Any]] = []
        for item in items:
            pos = _work_position_raw(item)
            f = _to_text(item.get("from") or item.get("f"))
            t = _to_text(item.get("to") or item.get("t"))
            year = _to_text(item.get("year") or item.get("years") or item.get("period"))
            from_since = _to_text(
                item.get("from_since") or item.get("fs") or item.get("since") or ""
            )
            if f or t:
                norm_items.append(
                    {"from": f, "to": t, "position": pos, "from_since": from_since}
                )
            elif year or pos:
                norm_items.append({"year": year, "position": pos})
        out["work_experience"] = norm_items
    return out


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
    pos = _work_position_raw(item)
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

    from_since = _to_text(
        item.get("from_since") or item.get("fs") or item.get("since") or ""
    )

    return {
        "from_year": from_y,
        "to_year": to_y,
        "from_since": from_since,
        "position": pos,
        "is_current": is_current,
    }


def _work_position(item: dict[str, Any]) -> str:
    return _work_position_raw(item)


def _meaningful_position(item: dict[str, Any]) -> bool:
    pos = _work_position(item)
    return bool(pos) and not is_none_token(pos)


def _meaningful_work_row(item: dict[str, Any]) -> bool:
    if _meaningful_position(item):
        return True
    f = _to_text(item.get("from_year"))
    t = _to_text(item.get("to_year"))
    return bool(f or t)


def _resolve_current_display(
    items: list[dict[str, Any]],
    *,
    current_job: str = "",
    current_job_year: str = "",
    lang: str = "uz_lat",
) -> tuple[str, str]:
    job = (current_job or "").strip()
    year = (current_job_year or "").strip()
    since = ""
    if job and is_none_token(job):
        job = ""
        year = ""

    if not job:
        for item in items:
            if not (item.get("is_current") or is_present_year_token(item.get("to_year") or "")):
                continue
            pos = item.get("position") or ""
            if _meaningful_position(item):
                job = pos
            year = item.get("from_year") or year
            since = item.get("from_since") or ""
            break

    if job:
        if not since:
            for item in items:
                if _to_text(item.get("position")) == job and (
                    item.get("is_current")
                    or is_present_year_token(item.get("to_year") or "")
                ):
                    since = item.get("from_since") or ""
                    if not year:
                        year = item.get("from_year") or ""
                    break
        year = format_current_job_year(year, lang, since=since)
    elif year or since:
        year = format_current_job_year(year, lang, since=since)
    else:
        year = ""
    return job, year


def _mehnat_year_prefix(item: dict[str, Any], lang: str) -> str:
    f = _to_text(item.get("from_year"))
    t = _to_text(item.get("to_year"))
    lang_clean = (lang or "uz_lat").strip().lower()

    if lang_clean == "en":
        hv = "present"
        y_mark = "y."
        yy_mark = "yrs"
    elif lang_clean == "ru":
        hv = "н.в."
        y_mark = "г."
        yy_mark = "гг."
    else:
        cyr = lang_clean == "uz_cyr"
        hv = "ҳ.в." if cyr else "h.v."
        y_mark = "й." if cyr else "y."
        yy_mark = "йй." if cyr else "yy."

    if item.get("is_current") or is_present_year_token(t):
        if lang_clean == "en":
            return f"{f} - {hv}" if f else hv
        return f"{f} {y_mark} - {hv}" if f else hv

    if f and t and t not in ("h.v", "hv"):
        core = f"{f}-{t}"
        if lang_clean == "en":
            return core
        if lang_clean == "ru":
            return f"{core} {yy_mark}"
        if "yy" not in core.lower() and "йй" not in core:
            return f"{core} {yy_mark}"
        return core
    if f:
        if lang_clean == "en":
            return f
        if lang_clean == "ru":
            return f"{f} {y_mark}"
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
    from_since = ""
    if year and not re.fullmatch(r"\d{4}", (year or "").strip().rstrip(":")):
        _, month_key = _parse_since_detail(year, from_y)
        if month_key:
            from_since = year
    return items + [
        {
            "from_year": from_y,
            "from_since": from_since,
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
    raw = normalize_obyektivka_raw(raw or {})
    lang = _to_text(raw.get("lang")) or "uz_lat"
    explicit_job = _to_text(raw.get("current_job"))
    explicit_year = _to_text(raw.get("current_job_year"))
    if explicit_job and is_none_token(explicit_job):
        explicit_job = ""
        explicit_year = ""

    items = [_canonical_work_item(w) for w in _parse_work_list(raw)]
    items = [x for x in items if _meaningful_work_row(x)]

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


# JS naming parity (webapp/docs)
buildMalumotnomaData = build_malumotnoma_data
