"""AI voice pipeline: STT → extraction → field mapping."""
from __future__ import annotations

import json
import logging

from features.ai.gemini_client import (
    extract_obyektivka_data,
    generate_text_with_fallback,
    get_model,
    is_valid_transcription_text,
    transcribe_audio,
    _gcall,
)
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
]

_SKIP_VALUES = {"", "yo'q", "yoq", "йўқ", "йўқ.", "нет", "no", "n/a", "—", "-"}

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
                year = f"{w.get('from', '')}-{w.get('to', '')}".strip("-")
            pos = str(
                w.get("position")
                or w.get("description")
                or w.get("work_place")
                or w.get("place")
                or ""
            ).strip()
            if year or pos:
                normalized.append({"year": year, "position": pos})
        out["work_experience"] = normalized

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
    """Extract CV fields from transcribed speech via Gemini."""
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
        if not raw_text:
            return {}
        cleaned = raw_text.replace("```json", "").replace("```", "").strip()
        start, end = cleaned.find("{"), cleaned.rfind("}") + 1
        if start == -1 or end <= start:
            return {}
        parsed = json.loads(cleaned[start:end])
        return parsed if isinstance(parsed, dict) else {}
    except AiQuotaError:
        raise
    except Exception as e:
        logger.error("CV extraction error: %s", e)
        return {}


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
    data = await extract_cv_data(transcript)
    missing = get_missing_cv_fields(data) if data else ["Ma'lumot ajratilmadi"]
    return transcript, data, missing


async def process_text_for_obyektivka(text: str) -> tuple[str, dict, list[dict]]:
    transcript = (text or "").strip()
    if not transcript:
        return "", {}, [{"id": "text", "label": "Matn bo'sh"}]
    raw = await extract_obyektivka_data(transcript)
    data = map_obyektivka_fields(raw)
    missing = get_missing_oby_fields(data) if data else [{"id": "all", "label": "Ma'lumot ajratilmadi"}]
    return transcript, data, missing


async def process_voice_for_obyektivka(audio_path: str) -> tuple[str, dict, list[dict]]:
    transcript = (await transcribe_audio(audio_path) or "").strip()
    if not is_valid_transcription_text(transcript):
        return transcript, {}, [{"id": "audio", "label": "Ovoz tushunilmadi"}]
    return await process_text_for_obyektivka(transcript)
