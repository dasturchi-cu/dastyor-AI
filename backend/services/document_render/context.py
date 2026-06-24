"""Build normalized Obyektivka template context with render options."""

from __future__ import annotations

import json
from typing import Any

from backend.services.document_render.pii_mask import mask_relatives_for_preview, mask_text_for_preview
from backend.services.document_render.photo import process_passport_photo
from backend.services.document_render.watermark import (
    preview_banner_text,
    watermark_opacity,
    watermark_text,
)
from features.obyektivka.malumotnoma_data import build_malumotnoma_data
from features.obyektivka.none_values import field_or_none, is_none_token
from features.obyektivka.spacing_config import html_layout_css_vars


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
    lang = str(raw.get("lang") or "uz_lat")
    mdata = build_malumotnoma_data(raw)
    current_job = mdata["current_job"]
    current_job_year = mdata["current_job_year"]
    if is_none_token(current_job):
        current_job = ""
        current_job_year = ""
    work_items = mdata["work_experience"]

    img = _to_text(raw.get("img") or raw.get("photo_data"))
    if process_photo and img:
        img = process_passport_photo(img)

    relatives = _normalize_relatives(_parse_list(raw.get("relatives") or raw.get("rels")))
    if mask_pii:
        relatives = mask_relatives_for_preview(relatives)

    ctx: dict[str, Any] = {
        "lang": lang,
        "current_job": _maybe_mask(current_job, enabled=mask_pii),
        "current_job_year": _maybe_mask(current_job_year, enabled=mask_pii),
        "img": img,
        "fullname": _to_text(raw.get("fullname")),
        "birthdate": _maybe_mask(_to_text(raw.get("birthdate") or raw.get("birth")), enabled=mask_pii),
        "birthplace": _maybe_mask(_to_text(raw.get("birthplace") or raw.get("place")), enabled=mask_pii),
        "nation": field_or_none(_to_text(raw.get("nation")), lang),
        "party": field_or_none(_to_text(raw.get("party")), lang),
        "education": field_or_none(_to_text(raw.get("education") or raw.get("edu")), lang),
        "graduated": field_or_none(_to_text(raw.get("graduated") or raw.get("grad")), lang),
        "specialty": field_or_none(_to_text(raw.get("specialty") or raw.get("spec")), lang),
        "degree": field_or_none(_to_text(raw.get("degree") or raw.get("deg")), lang),
        "scientific_title": field_or_none(_to_text(raw.get("scientific_title") or raw.get("ttl")), lang),
        "languages": field_or_none(_to_text(raw.get("languages") or raw.get("langs")), lang),
        "military_rank": field_or_none(_to_text(raw.get("military_rank") or raw.get("mil")), lang),
        "awards": field_or_none(_to_text(raw.get("awards") or raw.get("award")), lang),
        "departmental_awards": field_or_none(
            _to_text(raw.get("departmental_awards") or raw.get("idor_awards") or raw.get("idor")),
            lang,
        ),
        "deputy": field_or_none(_to_text(raw.get("deputy") or raw.get("dep")), lang),
        "address": _maybe_mask(_to_text(raw.get("address")), enabled=mask_pii),
        "phone": _maybe_mask(_to_text(raw.get("phone")), enabled=mask_pii),
        "work_experience": work_items,
        "relatives": relatives,
        "layout": html_layout_css_vars(),
        "render": {
            "watermark": bool(watermark),
            "mask_pii": bool(mask_pii),
            "watermark_text": watermark_text(),
            "watermark_opacity": watermark_opacity(),
            "preview_banner": preview_banner_text() if watermark else "",
        },
    }
    return ctx
