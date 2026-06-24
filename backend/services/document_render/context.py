"""Build normalized Obyektivka template context with render options."""

from __future__ import annotations

import json
import re
from typing import Any

from backend.services.document_render.pii_mask import mask_relatives_for_preview, mask_text_for_preview
from backend.services.document_render.photo import process_passport_photo
from features.obyektivka.current_job import extract_current_job
from backend.services.document_render.watermark import (
    preview_banner_text,
    watermark_opacity,
    watermark_text,
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


def _normalize_work_item(item: dict[str, Any]) -> dict[str, str]:
    year = _to_text(item.get("year") or item.get("years") or item.get("from"))
    end = _to_text(item.get("to"))
    if not year and (item.get("f") or item.get("t")):
        f = _to_text(item.get("f"))
        t = _to_text(item.get("t"))
        year = f"{f}-{t}".strip("-") if f or t else ""
    position = _to_text(
        item.get("position") or item.get("desc") or item.get("job") or item.get("d") or item.get("description")
    )
    if year and end and "yy" not in year.lower():
        year = f"{year}-{end} yy."
    year = year.rstrip(".") if year else year
    return {"year": year, "position": position}


def _infer_current_job(work_items: list[dict[str, Any]]) -> tuple[str, str, list[dict[str, Any]]]:
    current_job = ""
    current_job_year = ""
    items = [dict(x) for x in work_items]

    for idx, item in enumerate(items):
        year_raw = _to_text(item.get("year") or item.get("from"))
        year_norm = re.sub(r"[\s.\-_/]", "", year_raw.lower())
        is_current = any(
            key in year_norm
            for key in ("hv", "hvgacha", "hozirgacha", "ҳв", "ҳвгача", "ҳозиргача", "present", "current")
        )
        position_raw = _to_text(item.get("position") or item.get("description") or item.get("job") or item.get("d"))
        if is_current and position_raw:
            current_job = position_raw
            from_raw = _to_text(item.get("from") or item.get("f"))
            if from_raw:
                current_job_year = from_raw
            else:
                match = re.search(r"(19|20)\d{2}", year_raw)
                if match:
                    current_job_year = match.group(0)
            items.pop(idx)
            break
    return current_job, current_job_year, items


def _normalize_relatives(raw: list) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for rel in raw or []:
        if not isinstance(rel, dict):
            continue
        out.append(
            {
                "degree": _to_text(rel.get("degree") or rel.get("type")),
                "fullname": _to_text(rel.get("fullname") or rel.get("name")),
                "birth_year_place": _to_text(rel.get("birth_year_place") or rel.get("birth")),
                "work_place": _to_text(rel.get("work_place") or rel.get("job")),
                "address": _to_text(rel.get("address") or rel.get("addr")),
            }
        )
    return out


def _maybe_mask(value: str, *, enabled: bool) -> str:
    if not enabled or not value:
        return value
    return mask_text_for_preview(value)


def build_obyektivka_render_context(
    raw: dict[str, Any],
    *,
    watermark: bool = False,
    mask_pii: bool = False,
    process_photo: bool = True,
) -> dict[str, Any]:
    """
    Single source of truth for preview + PDF export.
    `watermark` / `mask_pii` are enabled for unpaid live preview.
    """
    works_raw = _parse_list(raw.get("work_experience") or raw.get("works"))
    work_items = [_normalize_work_item(w) for w in works_raw]
    work_items = [w for w in work_items if w.get("year") or w.get("position")]

    lang_key = str(raw.get("lang") or "uz_lat")
    current_job = _to_text(raw.get("current_job"))
    current_job_year = _to_text(raw.get("current_job_year"))
    current_job, current_job_year, work_items = extract_current_job(
        work_items,
        current_job=current_job,
        current_job_year=current_job_year,
        lang=lang_key,
    )

    img = _to_text(raw.get("img") or raw.get("photo_data"))
    if process_photo and img:
        img = process_passport_photo(img)

    relatives = _normalize_relatives(_parse_list(raw.get("relatives") or raw.get("rels")))
    if mask_pii:
        relatives = mask_relatives_for_preview(relatives)

    ctx: dict[str, Any] = {
        "lang": raw.get("lang", "uz_lat"),
        "current_job": _maybe_mask(current_job, enabled=mask_pii),
        "current_job_year": _maybe_mask(current_job_year, enabled=mask_pii),
        "img": img,
        "fullname": _to_text(raw.get("fullname")),
        "birthdate": _maybe_mask(_to_text(raw.get("birthdate") or raw.get("birth")), enabled=mask_pii),
        "birthplace": _maybe_mask(_to_text(raw.get("birthplace") or raw.get("place")), enabled=mask_pii),
        "nation": _to_text(raw.get("nation")),
        "party": _to_text(raw.get("party")),
        "education": _to_text(raw.get("education") or raw.get("edu")),
        "graduated": _to_text(raw.get("graduated") or raw.get("grad")),
        "specialty": _to_text(raw.get("specialty") or raw.get("spec")),
        "degree": _to_text(raw.get("degree") or raw.get("deg")),
        "scientific_title": _to_text(raw.get("scientific_title") or raw.get("ttl")),
        "languages": _to_text(raw.get("languages") or raw.get("langs")),
        "military_rank": _to_text(raw.get("military_rank") or raw.get("mil")),
        "awards": _to_text(raw.get("awards") or raw.get("award")),
        "departmental_awards": _to_text(raw.get("departmental_awards") or raw.get("idor_awards") or raw.get("idor")),
        "deputy": _to_text(raw.get("deputy") or raw.get("dep")),
        "address": _maybe_mask(_to_text(raw.get("address")), enabled=mask_pii),
        "phone": _maybe_mask(_to_text(raw.get("phone")), enabled=mask_pii),
        "work_experience": work_items,
        "relatives": relatives,
        "render": {
            "watermark": bool(watermark),
            "mask_pii": bool(mask_pii),
            "watermark_text": watermark_text(),
            "watermark_opacity": watermark_opacity(),
            "preview_banner": preview_banner_text() if watermark else "",
        },
    }
    return ctx
