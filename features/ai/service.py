"""AI voice pipeline: STT → extraction → field mapping."""
from __future__ import annotations

import logging
import re

from features.ai.gemini_client import (
    extract_obyektivka_data,
    generate_text_with_fallback,
    is_valid_transcription_text,
    transcribe_audio,
)
from features.ai.reliable import (
    cv_extract_has_content,
    normalize_cv_data,
    parse_json_object,
)
from features.ai.text_heuristics import merge_fact_dicts, parse_cv_facts, parse_obyektivka_facts
from shared.ai_errors import AiQuotaError

logger = logging.getLogger(__name__)

__all__ = [
    "transcribe_audio",
    "extract_obyektivka_data",
    "extract_cv_data",
    "is_valid_transcription_text",
    "process_voice_for_cv",
    "process_voice_for_obyektivka",
    "get_missing_cv_fields",
    "get_missing_oby_fields",
    "map_obyektivka_fields",
    "count_cv_populated_fields",
    "count_oby_populated_fields",
    "cv_fill_is_acceptable",
    "oby_fill_is_acceptable",
]

_SKIP_VALUES = {"", "yo'q", "yoq", "йўқ", "йўқ.", "нет", "no", "n/a", "—", "-"}

_HV_YEAR_RE = re.compile(
    r"h\.?\s*v\.?|ҳ\.?\s*в|hozirgacha|ҳозиргача|present|current|yildan|йилдан",
    re.IGNORECASE,
)


def _normalize_oby_work_year(year: str) -> str:
    y = (year or "").strip()
    if not y:
        return y
    norm = re.sub(r"[\s.\-_/]", "", y.lower())
    if any(tok in norm for tok in ("hv", "hvgacha", "hozirgacha", "ҳв", "ҳвгача", "ҳозиргача", "present", "current")):
        m = re.search(r"(19|20)\d{2}", y)
        return f"{m.group(0)}-h.v." if m else "h.v."
    m = re.match(r"^(\d{4})\s*[-–—]\s*(\d{4})\s*(йй|yy)?\.?$", y, re.IGNORECASE)
    if m:
        return f"{m.group(1)}-{m.group(2)} yy."
    if re.match(r"^\d{4}-\d{4}$", y) and "yy" not in y.lower() and "йй" not in y:
        return f"{y} yy."
    return y


def _split_current_job_from_works(
    works: list[dict],
) -> tuple[str, str, list[dict]]:
    items = [dict(w) for w in works if isinstance(w, dict)]
    for idx, item in enumerate(items):
        year_raw = str(item.get("year") or item.get("period") or "").strip()
        year_norm = re.sub(r"[\s.\-_/]", "", year_raw.lower())
        is_current = any(
            tok in year_norm
            for tok in ("hv", "hvgacha", "hozirgacha", "ҳв", "ҳвгача", "ҳозиргача", "present", "current")
        ) or bool(_HV_YEAR_RE.search(year_raw))
        pos = str(
            item.get("position")
            or item.get("description")
            or item.get("work_place")
            or item.get("d")
            or ""
        ).strip()
        if is_current and pos:
            m = re.search(r"(19|20)\d{2}", year_raw)
            yr = m.group(0) if m else year_raw
            if yr and not yr.endswith(":"):
                yr = f"{yr}-yildan:" if "yildan" not in year_raw.lower() and "йилдан" not in year_raw else year_raw
            items.pop(idx)
            return pos, yr.rstrip(":"), items
    return "", "", items

# WebApp field id → (data keys, label)
OBY_FIELD_MAP = [
    ("fullname", ("fullname",), "F.I.Sh."),
    ("birthdate", ("birthdate",), "Tug'ilgan sana"),
    ("birthplace", ("birthplace",), "Tug'ilgan joy"),
    ("nation", ("nation",), "Millati"),
    ("edu", ("education",), "Ma'lumoti"),
    ("graduated", ("graduated",), "Tamomlagan OTM"),
    ("spec", ("specialty",), "Mutaxassisligi"),
    ("party", ("party",), "Partiyaviyligi"),
    ("degree", ("degree",), "Ilmiy darajasi"),
    ("scititle", ("scientific_title",), "Ilmiy unvoni"),
    ("langs", ("languages",), "Chet tillari"),
    ("awards", ("awards",), "Davlat mukofotlari"),
    ("deputy", ("deputy",), "Deputatligi"),
    ("photo", ("photo_data", "photo_base64"), "Rasm (3×4)"),
    ("work_experience", ("work_experience",), "Mehnat faoliyati"),
    ("relatives", ("relatives",), "Oila a'zolari"),
]


def _present(val) -> bool:
    if val is None:
        return False
    if isinstance(val, list):
        return len(val) > 0
    s = str(val).strip().lower()
    return bool(s) and s not in _SKIP_VALUES


def map_obyektivka_fields(raw: dict) -> dict:
    """Normalize Gemini JSON → consistent obyektivka payload."""
    if not isinstance(raw, dict):
        return {}

    out = dict(raw)

    # Aliases
    if not out.get("fullname"):
        for k in ("full_name", "fio", "name", "fish"):
            if _present(raw.get(k)):
                out["fullname"] = str(raw[k]).strip()
                break

    if not out.get("birthdate") and _present(raw.get("birth_date")):
        out["birthdate"] = str(raw["birth_date"]).strip()

    if not out.get("education") and _present(raw.get("edu")):
        out["education"] = str(raw["edu"]).strip()

    if not out.get("specialty") and _present(raw.get("spec")):
        out["specialty"] = str(raw["spec"]).strip()

    if not out.get("languages") and _present(raw.get("langs")):
        out["languages"] = str(raw["langs"]).strip()

    # work_experience normalization
    works = out.get("work_experience") or out.get("works") or []
    if isinstance(works, list):
        normalized = []
        for w in works:
            if not isinstance(w, dict):
                continue
            year = str(w.get("year") or w.get("period") or "").strip()
            if not year and (w.get("from") or w.get("to")):
                f = str(w.get("from") or "").strip()
                t = str(w.get("to") or "").strip()
                year = f"{f}-{t}".strip("-") if f or t else ""
            pos = str(
                w.get("position")
                or w.get("description")
                or w.get("work_place")
                or w.get("place")
                or w.get("d")
                or ""
            ).strip()
            if year or pos:
                normalized.append({"year": _normalize_oby_work_year(year), "position": pos})
        out["work_experience"] = normalized

    # Hozirgi ish (h.v.) — ajratib olish
    if not _present(out.get("current_job")):
        cj, cy, rest = _split_current_job_from_works(out.get("work_experience") or [])
        if cj:
            out["current_job"] = cj
            out["current_job_year"] = cy
            out["work_experience"] = rest

    # relatives normalization
    rels = out.get("relatives") or []
    if isinstance(rels, list):
        normalized_rels = []
        for r in rels:
            if not isinstance(r, dict):
                continue
            degree = str(r.get("degree") or r.get("type") or r.get("relation") or "").strip()
            fullname = str(r.get("fullname") or r.get("name") or "").strip()
            if degree or fullname:
                normalized_rels.append(
                    {
                        "degree": degree,
                        "fullname": fullname,
                        "birth_year_place": str(
                            r.get("birth_year_place") or r.get("birth") or ""
                        ).strip(),
                        "work_place": str(
                            r.get("work_place") or r.get("job") or r.get("position") or ""
                        ).strip(),
                        "address": str(r.get("address") or r.get("addr") or "").strip(),
                    }
                )
        out["relatives"] = normalized_rels

    # Default yo'q for optional text fields
    for key in ("party", "degree", "scientific_title", "awards", "deputy", "military_rank"):
        if not _present(out.get(key)):
            out[key] = "yo'q"
    if not _present(out.get("languages")):
        out["languages"] = "yo'q"

    return out


def get_missing_oby_fields(data: dict) -> list[dict]:
    """Return missing fields with id + label for WebApp highlighting."""
    missing: list[dict] = []
    if not data:
        return [{"id": "all", "label": "Ma'lumot ajratilmadi"}]

    for field_id, keys, label in OBY_FIELD_MAP:
        if field_id == "photo":
            if not _present(data.get("photo_data")) and not _present(data.get("photo_base64")):
                missing.append({"id": field_id, "label": label})
            continue
        if field_id == "work_experience":
            if not data.get("work_experience"):
                missing.append({"id": field_id, "label": label})
            continue
        if field_id == "relatives":
            if not data.get("relatives"):
                missing.append({"id": field_id, "label": label})
            continue
        found = any(_present(data.get(k)) for k in keys)
        if not found:
            missing.append({"id": field_id, "label": label})
    return missing


async def extract_cv_data(text: str) -> dict:
    """Extract CV fields from transcribed speech via Gemini + local heuristics."""
    heuristic = normalize_cv_data(parse_cv_facts(text))
    prompt = f"""
Quyidagi matndan CV uchun faktlarni JSONga ajrat.
Qoidalar:
- Faqat aniq aytilgan ma'lumotni joylashtir, qolgani bo'sh string yoki bo'sh ro'yxat.
- name: "Familiya Ism" formatida.
- works: [{{"title": "lavozim", "company": "korxona", "from": "yil", "to": "yil", "description": "..."}}]
- education_list: [{{"title": "mutaxassislik", "company": "OTM", "date": "yillar"}}]
- languages_list: [{{"lang": "til", "listen": 0-6, "read": 0-6, "speak": 0-6, "write": 0-6}}]
- Javob faqat JSON (markdownsiz).

Matn: {text}

JSON:
{{
  "name": "",
  "phone": "",
  "email": "",
  "loc": "",
  "birthdate": "",
  "about": "",
  "spec": "",
  "skills": "",
  "works": [],
  "education_list": [],
  "languages_list": []
}}
"""
    try:
        raw_text = await generate_text_with_fallback(prompt, timeout=35)
        ai_data: dict = {}
        if raw_text:
            parsed = parse_json_object(raw_text)
            if isinstance(parsed, dict):
                ai_data = normalize_cv_data(parsed)
        merged = normalize_cv_data(merge_fact_dicts(ai_data, heuristic))
        if cv_extract_has_content(merged):
            return merged
        return heuristic if cv_extract_has_content(heuristic) else {}
    except AiQuotaError:
        raise
    except Exception as e:
        logger.error("CV extraction error: %s", e)
        return heuristic if cv_extract_has_content(heuristic) else {}


def count_cv_populated_fields(data: dict | None) -> int:
    """Count non-empty CV scalar/list fields extracted for WebApp autofill."""
    if not data:
        return 0
    count = sum(
        1
        for key in ("name", "phone", "email", "loc", "spec", "about", "birthdate")
        if _present(data.get(key))
    )
    if data.get("works"):
        count += 1
    if data.get("education_list"):
        count += 1
    if data.get("skills"):
        count += 1
    return count


def count_oby_populated_fields(data: dict | None) -> int:
    """Count non-empty obyektivka fields (excludes default yo'q placeholders)."""
    if not data:
        return 0
    count = 0
    for field_id, keys, _label in OBY_FIELD_MAP:
        if field_id == "photo":
            if any(_present(data.get(k)) for k in keys):
                count += 1
            continue
        if field_id == "work_experience":
            if data.get("work_experience"):
                count += 1
            continue
        if field_id == "relatives":
            if data.get("relatives"):
                count += 1
            continue
        if any(_present(data.get(k)) for k in keys):
            count += 1
    return count


def cv_fill_is_acceptable(data: dict | None, missing: list[str] | None = None) -> bool:
    if count_cv_populated_fields(data) < 1:
        return False
    name = str(data.get("name") or "").strip()
    if not name:
        return False
    extras = sum(
        1
        for key in ("phone", "email", "loc", "spec", "about")
        if str(data.get(key) or "").strip()
    )
    has_lists = bool(data.get("works")) or bool(data.get("education_list"))
    if extras + (1 if has_lists else 0) < 1:
        return False
    if missing is not None and len(missing) >= 6:
        return False
    return True


def oby_fill_is_acceptable(data: dict | None) -> bool:
    return count_oby_populated_fields(data) >= 1 and bool(str(data.get("fullname") or "").strip())


def get_missing_cv_fields(data: dict) -> list[str]:
    missing = []
    labels = {
        "name": "F.I.SH",
        "phone": "Telefon",
        "email": "Email",
        "loc": "Manzil",
        "birthdate": "Tug'ilgan sana",
    }
    for key, label in labels.items():
        if not str(data.get(key) or "").strip():
            missing.append(label)
    if not data.get("works") and not data.get("education_list"):
        missing.append("Tajriba yoki Ta'lim")
    return missing


async def process_voice_for_cv(audio_path: str) -> tuple[str, dict, list[str]]:
    transcript = (await transcribe_audio(audio_path) or "").strip()
    if not is_valid_transcription_text(transcript):
        return transcript, {}, ["Ovoz tushunilmadi"]
    return await process_text_for_cv(transcript)


async def process_text_for_cv(text: str) -> tuple[str, dict, list[str]]:
    transcript = (text or "").strip()
    if not transcript:
        return "", {}, ["Matn bo'sh"]
    data = normalize_cv_data(await extract_cv_data(transcript))
    missing = get_missing_cv_fields(data) if data else ["Ma'lumot ajratilmadi"]
    if not cv_fill_is_acceptable(data, missing):
        return transcript, {}, missing or ["Ma'lumot ajratilmadi"]
    return transcript, data, missing


async def process_text_for_obyektivka(text: str) -> tuple[str, dict, list[dict]]:
    transcript = (text or "").strip()
    if not transcript:
        return "", {}, [{"id": "text", "label": "Matn bo'sh"}]
    heuristic = parse_obyektivka_facts(transcript)
    raw = await extract_obyektivka_data(transcript)
    merged_raw = merge_fact_dicts(raw, heuristic)
    data = map_obyektivka_fields(merged_raw)
    if not oby_fill_is_acceptable(data):
        return transcript, {}, [{"id": "all", "label": "Ma'lumot ajratilmadi"}]
    missing = get_missing_oby_fields(data)
    return transcript, data, missing


async def process_voice_for_obyektivka(audio_path: str) -> tuple[str, dict, list[dict]]:
    transcript = (await transcribe_audio(audio_path) or "").strip()
    if not is_valid_transcription_text(transcript):
        return transcript, {}, [{"id": "audio", "label": "Ovoz tushunilmadi"}]
    return await process_text_for_obyektivka(transcript)
