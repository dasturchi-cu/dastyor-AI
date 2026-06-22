"""Reliable AI helpers — JSON parsing, retries, response validation."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Awaitable, Callable, TypeVar

from shared.ai_errors import AiQuotaError, is_quota_error, is_transient_ai_error

logger = logging.getLogger(__name__)

T = TypeVar("T")

_SKIP_VALUES = frozenset({"", "yo'q", "yoq", "йўқ", "нет", "no", "none", "n/a", "—", "-"})


def parse_json_object(text: str | None) -> dict[str, Any] | None:
    """Extract the first JSON object from LLM output (markdown fences tolerated)."""
    if not text or not str(text).strip():
        return None

    cleaned = str(text).replace("```json", "").replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end <= start:
        return None

    blob = cleaned[start : end + 1]
    parsed = _loads_json_lenient(blob)
    return parsed if isinstance(parsed, dict) else None


def _loads_json_lenient(blob: str) -> Any | None:
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        repaired = re.sub(r",\s*([}\]])", r"\1", blob)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            return None


def response_text_or_empty(response: Any) -> str:
    """Safely read `.text` from a Gemini response object."""
    if response is None:
        return ""
    text = getattr(response, "text", None)
    if text:
        return str(text).strip()
    try:
        candidates = getattr(response, "candidates", None) or []
        for cand in candidates:
            content = getattr(cand, "content", None)
            parts = getattr(content, "parts", None) or []
            chunks: list[str] = []
            for part in parts:
                t = getattr(part, "text", None)
                if t:
                    chunks.append(str(t))
            if chunks:
                return "".join(chunks).strip()
    except Exception:
        pass
    return ""


async def retry_ai(
    factory: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay: float = 0.6,
    label: str = "ai",
) -> T:
    """Retry transient AI failures; quota errors fail immediately."""
    last_exc: Exception | None = None
    for attempt in range(1, max(1, attempts) + 1):
        try:
            return await factory()
        except AiQuotaError:
            raise
        except Exception as exc:
            if is_quota_error(exc):
                raise AiQuotaError(str(exc)) from exc
            last_exc = exc
            if not is_transient_ai_error(exc) or attempt >= attempts:
                raise
            delay = base_delay * attempt
            logger.warning("%s transient error (attempt %s/%s): %s", label, attempt, attempts, exc)
            await asyncio.sleep(delay)
    if last_exc:
        raise last_exc
    raise RuntimeError(f"{label} retry exhausted")


def _has_meaningful_scalar(val: Any) -> bool:
    if val is None:
        return False
    s = str(val).strip().lower()
    return bool(s) and s not in _SKIP_VALUES


def cv_extract_has_content(data: dict[str, Any] | None) -> bool:
    if not data:
        return False
    for key in ("name", "phone", "email", "about", "spec", "loc", "birthdate"):
        if _has_meaningful_scalar(data.get(key)):
            return True
    for key in ("works", "education_list", "languages_list"):
        val = data.get(key)
        if isinstance(val, list) and len(val) > 0:
            return True
    return False


def oby_extract_has_content(data: dict[str, Any] | None) -> bool:
    if not data:
        return False
    for key, val in data.items():
        if key == "relatives" and isinstance(val, list):
            for rel in val:
                if isinstance(rel, dict) and any(_has_meaningful_scalar(x) for x in rel.values()):
                    return True
            continue
        if key == "work_experience" and isinstance(val, list):
            for work in val:
                if isinstance(work, dict) and any(_has_meaningful_scalar(x) for x in work.values()):
                    return True
            continue
        if _has_meaningful_scalar(val):
            return True
    return False


def normalize_cv_data(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize Gemini CV JSON → stable WebApp payload."""
    if not isinstance(raw, dict):
        return {}

    out = dict(raw)

    if not _has_meaningful_scalar(out.get("name")):
        for alias in ("fullname", "full_name", "fio", "fish"):
            if _has_meaningful_scalar(out.get(alias)):
                out["name"] = str(out[alias]).strip()
                break

    if not _has_meaningful_scalar(out.get("loc")) and _has_meaningful_scalar(out.get("location")):
        out["loc"] = str(out["location"]).strip()

    if not _has_meaningful_scalar(out.get("spec")) and _has_meaningful_scalar(out.get("specialty")):
        out["spec"] = str(out["specialty"]).strip()

    for key, val in list(out.items()):
        if isinstance(val, str):
            out[key] = val.strip()

    works = out.get("works") or out.get("work_experience") or []
    if isinstance(works, list):
        normalized: list[dict[str, str]] = []
        for item in works:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("position") or "").strip()
            company = str(item.get("company") or item.get("employer") or item.get("place") or "").strip()
            if title or company:
                normalized.append(
                    {
                        "title": title,
                        "company": company,
                        "from": str(item.get("from") or item.get("start") or "").strip(),
                        "to": str(item.get("to") or item.get("end") or "").strip(),
                        "description": str(item.get("description") or item.get("details") or "").strip(),
                    }
                )
        out["works"] = normalized

    edu = out.get("education_list") or out.get("education") or []
    if isinstance(edu, list):
        edu_norm: list[dict[str, str]] = []
        for item in edu:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("degree") or item.get("specialty") or "").strip()
            company = str(item.get("company") or item.get("school") or item.get("university") or "").strip()
            if title or company:
                edu_norm.append(
                    {
                        "title": title,
                        "company": company,
                        "date": str(item.get("date") or item.get("years") or item.get("year") or "").strip(),
                    }
                )
        out["education_list"] = edu_norm

    for alias in ("fullname", "full_name", "fio", "fish", "location", "specialty", "work_experience", "education"):
        out.pop(alias, None)

    return out
