"""Lightweight fact extraction from free-form Uzbek CV / obyektivka text."""
from __future__ import annotations

import re
from typing import Any


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


_LABEL_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"(?:full\s*name|ism(?:\s*(?:va\s*)?familiya)?|f\.?\s*i\.?\s*sh\.?|name)\s*[:\-–]\s*(.+)",
            re.I,
        ),
        "name",
    ),
    (
        re.compile(
            r"(?:birth\s*date|tug[''`ʻʼ]ilgan\s*sana|tug[''`ʻʼ]ilgan\s*sanasi)\s*[:\-–]\s*(.+)",
            re.I,
        ),
        "birthdate",
    ),
    (
        re.compile(
            r"(?:birth\s*place|tug[''`ʻʼ]ilgan\s*joyi?|manzil)\s*[:\-–]\s*(.+)",
            re.I,
        ),
        "loc",
    ),
    (
        re.compile(
            r"(?:specialty|speciality|kasb|mutaxassislik|lavozim|profession)\s*[:\-–]\s*(.+)",
            re.I,
        ),
        "spec",
    ),
    (
        re.compile(r"(?:phone|telefon|tel)\s*[:\-–]\s*(.+)", re.I),
        "phone",
    ),
    (
        re.compile(r"(?:e-?mail|email)\s*[:\-–]\s*(.+)", re.I),
        "email",
    ),
    (
        re.compile(
            r"(?:education|ta[''`ʻʼ]lim|o[''`ʻʼ]qish)\s*[:\-–]\s*(.+)",
            re.I,
        ),
        "_education_inline",
    ),
    (
        re.compile(
            r"(?:work\s*experience|ish\s+tajribasi|tajriba|experience)\s*[:\-–]\s*(.+)",
            re.I,
        ),
        "_experience_inline",
    ),
    (
        re.compile(
            r"(?:skills?|ko[''`ʻʼ]nikmalar|texnologiyalar)\s*[:\-–]\s*(.+)",
            re.I,
        ),
        "skills",
    ),
    (
        re.compile(r"(?:languages?|tillar)\s*[:\-–]\s*(.+)", re.I),
        "_languages_inline",
    ),
]

_SECTION_HEADERS = {
    "skills": re.compile(
        r"^\s*(skills?|ko[''`ʻʼ]nikmalar|ko'nikma|texnologiyalar|competenc(?:e|ies)|навыки)\s*[:\-–]?\s*$",
        re.I,
    ),
    "experience": re.compile(
        r"^\s*(experience|tajriba|ish\s+tajribasi|work\s+experience|mehnat\s+faoliyati|опыт)\s*[:\-–]?\s*$",
        re.I,
    ),
    "education": re.compile(
        r"^\s*(education|ta[''`ʻʼ]lim|o[''`ʻʼ]qish|образование)\s*[:\-–]?\s*$",
        re.I,
    ),
    "languages": re.compile(
        r"^\s*(languages?|tillar|языки)\s*[:\-–]?\s*$",
        re.I,
    ),
}


def _split_sections(text: str) -> dict[str, str]:
    t = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in t.split("\n")]
    current = "general"
    out: dict[str, list[str]] = {current: []}

    for ln in lines:
        if not ln.strip():
            out.setdefault(current, []).append("")
            continue
        moved = False
        for key, rx in _SECTION_HEADERS.items():
            if rx.match(ln):
                current = key
                out.setdefault(current, [])
                moved = True
                break
        if moved:
            continue
        out.setdefault(current, []).append(ln)

    return {k: "\n".join(v).strip() for k, v in out.items() if "\n".join(v).strip()}


def _guess_name_from_first_line(text: str) -> str | None:
    first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    first = _clean(first)
    if not first or len(first) > 80:
        return None
    if re.search(r"[@+]|:\s", first):
        return None
    if re.match(
        r"^(?:full\s*name|ism|birth|tug[''`ʻʼ]ilgan|education|ta[''`ʻʼ]lim|skills|ko[''`ʻʼ]nikma|languages|tillar|work|ish|specialty|kasb)",
        first,
        re.I,
    ):
        return None
    parts = [p for p in re.split(r"\s+", first) if p]
    if len(parts) < 2:
        return None
    return first.title()


def _parse_skills_text(section: str) -> str:
    items = re.split(r"[\n•\-–—,;]+", section or "")
    skills = []
    seen: set[str] = set()
    for item in items:
        it = _clean(item)
        if not it or len(it) > 60:
            continue
        key = it.lower()
        if key in seen:
            continue
        seen.add(key)
        skills.append(it)
    return ", ".join(skills[:40])


def _parse_education_entry(text: str) -> dict[str, str] | None:
    s = _clean(text)
    if not s:
        return None
    year_m = re.search(r"(\d{4})\s*[-–]\s*(\d{4})", s)
    if year_m:
        rest = _clean(s[year_m.end() :])
        company = rest
        title = ""
        if "," in rest:
            parts = [p.strip() for p in rest.split(",", 1)]
            company = parts[0]
            title = parts[1] if len(parts) > 1 else ""
        return {
            "company": company,
            "title": title,
            "date": f"{year_m.group(1)}-{year_m.group(2)}",
        }
    # "OTM da fan bo'yicha" style
    edu_m = re.search(
        r"(.+?)\s+da\s+(.+?)\s+bo\W*yicha\s+o\W*qidim",
        s,
        re.I,
    )
    if edu_m:
        return {
            "company": _clean(edu_m.group(1)),
            "title": _clean(edu_m.group(2)),
            "date": "",
        }
    return {"company": s, "title": "", "date": ""}


def _parse_work_entry(text: str) -> dict[str, str] | None:
    s = _clean(text)
    if not s:
        return None
    year_m = re.search(r"(\d{4})\s*[-–]\s*(\d{4})", s)
    if year_m:
        rest = _clean(s[year_m.end() :].lstrip("-–— "))
        title = rest
        company = ""
        if "—" in rest or " - " in rest:
            parts = re.split(r"\s*[—\-]\s*", rest, maxsplit=1)
            title = parts[0].strip()
            company = parts[1].strip() if len(parts) > 1 else ""
        return {
            "from": year_m.group(1),
            "to": year_m.group(2),
            "title": title,
            "company": company,
            "description": "",
        }
    work_m = re.search(r"(\d{4})\s*-?(?:yil)?dan\s+beri\s+(.+?)(?:\s*ishlayman)?$", s, re.I)
    if work_m:
        company = _clean(work_m.group(2))
        company = re.sub(r"da$", "", company, flags=re.I).strip()
        return {
            "from": work_m.group(1),
            "to": "hozir",
            "company": company,
            "title": "",
            "description": "",
        }
    return {"from": "", "to": "", "title": s, "company": "", "description": ""}


def _parse_languages_text(text: str) -> list[dict[str, Any]]:
    items = re.split(r"[\n•;]+", text or "")
    out: list[dict[str, Any]] = []
    for item in items:
        lang = _clean(re.split(r"[,\-–—]", item, maxsplit=1)[0])
        if not lang or len(lang) > 40:
            continue
        out.append({"lang": lang, "listen": 0, "read": 0, "speak": 0, "write": 0})
    return out[:20]


def _apply_structured_labels(t: str, out: dict[str, Any]) -> None:
    for rx, key in _LABEL_PATTERNS:
        m = rx.search(t)
        if not m:
            continue
        val = _clean(m.group(1))
        if not val:
            continue
        if key == "_education_inline":
            entry = _parse_education_entry(val)
            if entry and not out.get("education_list"):
                out["education_list"] = [entry]
        elif key == "_experience_inline":
            entry = _parse_work_entry(val)
            if entry and not out.get("works"):
                out["works"] = [entry]
        elif key == "_languages_inline":
            langs = _parse_languages_text(val)
            if langs and not out.get("languages_list"):
                out["languages_list"] = langs
        elif key == "skills" and not out.get("skills"):
            out["skills"] = _parse_skills_text(val)
        elif key == "phone":
            phone = re.sub(r"\s+", "", val)
            if phone and not out.get("phone"):
                out["phone"] = phone
        elif key == "email":
            email_m = re.search(r"[\w.+-]+@[\w.-]+\.\w+", val)
            if email_m and not out.get("email"):
                out["email"] = email_m.group(0)
        elif not out.get(key):
            out[key] = val if key == "name" else val


def _apply_sections(t: str, out: dict[str, Any]) -> None:
    sections = _split_sections(t)
    if not out.get("skills") and sections.get("skills"):
        out["skills"] = _parse_skills_text(sections["skills"])
    if not out.get("education_list") and sections.get("education"):
        entries = []
        for block in re.split(r"\n\s*\n", sections["education"]):
            entry = _parse_education_entry(block)
            if entry:
                entries.append(entry)
        if entries:
            out["education_list"] = entries
    if not out.get("works") and sections.get("experience"):
        entries = []
        for ln in sections["experience"].splitlines():
            entry = _parse_work_entry(ln)
            if entry:
                entries.append(entry)
        if entries:
            out["works"] = entries
    if not out.get("languages_list") and sections.get("languages"):
        langs = _parse_languages_text(sections["languages"])
        if langs:
            out["languages_list"] = langs


def parse_cv_facts(text: str) -> dict[str, Any]:
    t = (text or "").strip()
    if not t:
        return {}

    out: dict[str, Any] = {}

    _apply_structured_labels(t, out)
    _apply_sections(t, out)

    name_m = re.search(
        r"Men\s+([A-Za-zÀ-ÿ''ʻ`\-]+(?:\s+[A-Za-zÀ-ÿ''ʻ`\-]+){0,3})m(?:an|en)\b",
        t,
        re.I,
    )
    if name_m and not out.get("name"):
        out["name"] = _clean(name_m.group(1)).title()

    if not out.get("name"):
        guessed = _guess_name_from_first_line(t)
        if guessed:
            out["name"] = guessed

    phone_m = re.search(r"\+998\s*\d{2}\s*\d{3}\s*\d{2}\s*\d{2}", t)
    if phone_m and not out.get("phone"):
        out["phone"] = re.sub(r"\s+", "", phone_m.group(0))
    elif not out.get("phone"):
        phone_m = re.search(r"(?:\+?998|8)\s*(\d{2})[\s-]?(\d{3})[\s-]?(\d{2})[\s-]?(\d{2})", t)
        if phone_m:
            out["phone"] = f"+998{phone_m.group(1)}{phone_m.group(2)}{phone_m.group(3)}{phone_m.group(4)}"

    if not out.get("email"):
        email_m = re.search(r"[\w.+-]+@[\w.-]+\.\w+", t)
        if email_m:
            out["email"] = email_m.group(0)

    if not out.get("loc"):
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

    if not out.get("spec"):
        spec_m = re.search(r"([\w''ʻ`\-\s]+?)\s+dasturchim(?:an|en)\b", t, re.I)
        if spec_m:
            out["spec"] = _clean(spec_m.group(1)).title() + " dasturchi"
        elif re.search(r"dasturchi", t, re.I):
            out["spec"] = "Dasturchi"

    if not out.get("education_list"):
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

    if not out.get("works"):
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
