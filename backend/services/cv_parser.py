from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CvParseResult:
    name: str | None
    skills: list[str]
    experience: list[dict]
    raw_sections: dict[str, str]


_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")


def _clean(s: str) -> str:
    return re.sub(r"[ \t]+", " ", (s or "").strip())


def _split_sections(text: str) -> dict[str, str]:
    """
    Lightweight sectionizer for CV text (works for uz/ru/en).
    """
    t = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in t.split("\n")]

    headers = {
        "skills": re.compile(r"^\s*(skills?|ko['’`ʻʼ]nikmalar|ko'nikma|texnologiyalar|competenc(?:e|ies)|навыки|технологии)\s*[:\-]?\s*$", re.IGNORECASE),
        "experience": re.compile(r"^\s*(experience|tajriba|ish\s+tajribasi|work\s+experience|опыт\s+работы|опыт)\s*[:\-]?\s*$", re.IGNORECASE),
        "education": re.compile(r"^\s*(education|ta['’`ʻʼ]lim|o['’`ʻʼ]qish|образование)\s*[:\-]?\s*$", re.IGNORECASE),
        "summary": re.compile(r"^\s*(summary|about|profile|men\s+haqimda|о\s+себе|профиль)\s*[:\-]?\s*$", re.IGNORECASE),
    }

    current = "general"
    out: dict[str, list[str]] = {current: []}

    for ln in lines:
        if not ln.strip():
            out.setdefault(current, []).append("")
            continue
        moved = False
        for key, rx in headers.items():
            if rx.match(ln):
                current = key
                out.setdefault(current, [])
                moved = True
                break
        if moved:
            continue
        out.setdefault(current, []).append(ln)

    return {k: "\n".join(v).strip() for k, v in out.items() if "\n".join(v).strip()}


def _guess_name(text: str) -> str | None:
    t = (text or "").strip()
    if not t:
        return None
    # First non-empty line often contains the name
    first = next((ln.strip() for ln in t.splitlines() if ln.strip()), "")
    first = _clean(first)
    # Avoid lines that are email/phone/title
    if _EMAIL_RE.search(first) or _PHONE_RE.search(first):
        return None
    # If it's too long, it's not a name
    if len(first) > 60:
        return None
    # Require at least two words
    parts = [p for p in re.split(r"\s+", first) if p]
    if len(parts) < 2:
        return None
    return first


def _parse_skills(section: str) -> list[str]:
    s = (section or "").strip()
    if not s:
        return []
    # Split by commas / bullets / newlines
    raw = re.split(r"[\n•\-–—,;]+", s)
    skills = []
    seen = set()
    for item in raw:
        it = _clean(item)
        if not it:
            continue
        if len(it) > 50:
            continue
        key = it.lower()
        if key in seen:
            continue
        seen.add(key)
        skills.append(it)
    return skills[:60]


def _parse_experience(section: str) -> list[dict]:
    s = (section or "").strip()
    if not s:
        return []
    lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
    out: list[dict] = []
    cur: dict | None = None
    for ln in lines:
        # A new role line often contains a year range
        if re.search(r"\b(19\d{2}|20\d{2})\b", ln) and (cur is None or len(cur.get("details", "")) > 220):
            if cur:
                out.append(cur)
            cur = {"title": _clean(ln)[:160], "details": ""}
            continue
        if cur is None:
            cur = {"title": _clean(ln)[:160], "details": ""}
            continue
        det = (cur.get("details") or "")
        det = (det + ("\n" if det else "") + ln).strip()
        cur["details"] = det[:1200]
    if cur:
        out.append(cur)
    return out[:30]


def parse_cv_text(text: str) -> CvParseResult:
    sections = _split_sections(text)
    name = _guess_name(text)
    skills = _parse_skills(sections.get("skills", ""))
    experience = _parse_experience(sections.get("experience", ""))
    return CvParseResult(
        name=name,
        skills=skills,
        experience=experience,
        raw_sections=sections,
    )

