"""Lightweight fact extraction from free-form Uzbek CV / obyektivka text."""
from __future__ import annotations

import re
from typing import Any


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def parse_cv_facts(text: str) -> dict[str, Any]:
    t = (text or "").strip()
    if not t:
        return {}

    out: dict[str, Any] = {}

    name_m = re.search(
        r"Men\s+([A-Za-zÀ-ÿ''ʻ`\-]+(?:\s+[A-Za-zÀ-ÿ''ʻ`\-]+){0,3})m(?:an|en)\b",
        t,
        re.I,
    )
    if name_m:
        out["name"] = _clean(name_m.group(1)).title()

    phone_m = re.search(r"\+998\s*\d{2}\s*\d{3}\s*\d{2}\s*\d{2}", t)
    if phone_m:
        out["phone"] = re.sub(r"\s+", "", phone_m.group(0))
    else:
        phone_m = re.search(r"(?:\+?998|8)\s*(\d{2})[\s-]?(\d{3})[\s-]?(\d{2})[\s-]?(\d{2})", t)
        if phone_m:
            out["phone"] = f"+998{phone_m.group(1)}{phone_m.group(2)}{phone_m.group(3)}{phone_m.group(4)}"

    email_m = re.search(r"[\w.+-]+@[\w.-]+\.\w+", t)
    if email_m:
        out["email"] = email_m.group(0)

    loc_m = re.search(r"([\w''ʻ`\-\s]+?)\s+shahri?man", t, re.I)
    if loc_m:
        out["loc"] = _clean(loc_m.group(1)).title() + " shahri"
    else:
        loc_m = re.search(r"([\w''ʻ`\-\s]+?)\s+viloyati?man", t, re.I)
        if loc_m:
            out["loc"] = _clean(loc_m.group(1)).title() + " viloyati"
    if not out.get("loc"):
        loc_m = re.search(r"Toshkent(?:\s+shahri)?", t, re.I)
        if loc_m:
            out["loc"] = "Toshkent shahri"

    spec_m = re.search(r"([\w''ʻ`\-\s]+?)\s+dasturchim(?:an|en)\b", t, re.I)
    if spec_m:
        out["spec"] = _clean(spec_m.group(1)).title() + " dasturchi"
    else:
        spec_m = re.search(r"([\w''ʻ`\-\s]+?)(?:man|men)\.", t, re.I)
        if spec_m and not name_m:
            pass
        elif re.search(r"dasturchi", t, re.I):
            out["spec"] = "Dasturchi"

    edu_m = re.search(
        r"(\d{4})\s*[-–]\s*(\d{4})\s+(.+?)\s+da\s+(.+?)\s+bo\W*yicha\s+o\W*qidim",
        t,
        re.I,
    )
    if edu_m:
        out["education_list"] = [
            {
                "company": _clean(edu_m.group(3)),
                "title": _clean(edu_m.group(4)),
                "date": f"{edu_m.group(1)}-{edu_m.group(2)}",
            }
        ]

    work_m = re.search(
        r"(\d{4})\s*-?(?:yil)?dan\s+beri\s+(.+?)\s*ishlayman",
        t,
        re.I,
    )
    if work_m:
        company = _clean(work_m.group(2))
        company = re.sub(r"da$", "", company, flags=re.I).strip()
        out["works"] = [
            {
                "from": work_m.group(1),
                "to": "hozir",
                "company": company,
                "title": out.get("spec", ""),
            }
        ]

    if not out.get("about") and len(t) > 20:
        out["about"] = t[:500]

    return out


def parse_obyektivka_facts(text: str) -> dict[str, Any]:
    cv = parse_cv_facts(text)
    if not cv:
        return {}

    out: dict[str, Any] = {}
    if cv.get("name"):
        out["fullname"] = cv["name"]
    if cv.get("loc"):
        out["birthplace"] = cv["loc"]
    if cv.get("spec"):
        out["specialty"] = cv["spec"]

    edu_list = cv.get("education_list") or []
    if edu_list:
        edu = edu_list[0]
        out["education"] = "oliy"
        out["graduated"] = _clean(f"{edu.get('date', '')} {edu.get('company', '')}")
        if edu.get("title"):
            out["specialty"] = edu["title"]

    works = cv.get("works") or []
    if works:
        out["work_experience"] = []
        for w in works:
            year = w.get("from") or ""
            if year:
                year = f"{year}-h.v."
            pos = _clean(f"{w.get('title', '')} — {w.get('company', '')}".strip(" —"))
            out["work_experience"].append({"year": year, "position": pos})

    return out


def merge_fact_dicts(base: dict[str, Any] | None, extra: dict[str, Any] | None) -> dict[str, Any]:
    """Merge dicts; scalar values from extra fill only empty slots, lists extend."""
    out: dict[str, Any] = dict(base or {})
    for key, val in (extra or {}).items():
        if val is None:
            continue
        if isinstance(val, list):
            if val and not out.get(key):
                out[key] = list(val)
            continue
        if isinstance(val, str):
            if val.strip() and not str(out.get(key) or "").strip():
                out[key] = val.strip()
            continue
        if not out.get(key):
            out[key] = val
    return out
