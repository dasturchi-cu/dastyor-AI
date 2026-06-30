"""Single data mapper for all Obyektivka outputs (preview, demo, paid DOCX)."""

from __future__ import annotations

import json
from typing import Any

from features.obyektivka.layout import labels_for
from features.obyektivka.malumotnoma_data import build_malumotnoma_data
from features.obyektivka.none_values import field_or_none

NONE_UZ = "yo'q"
NONE_CYR = "йўқ"

# Canonical English keys → master template placeholder keys (locked asset).
TEMPLATE_KEY_MAP: dict[str, str] = {
    "full_name": "fish",
    "birth_date": "tugilgan_sana",
    "birth_place": "tugilgan_joy",
    "nationality": "millati",
    "party_membership": "partiyaviyligi",
    "education": "malumoti",
    "graduated_university": "tamomlagan",
    "speciality": "mutaxassisligi",
    "academic_degree": "ilmiy_darajasi",
    "academic_title": "ilmiy_unvoni",
    "languages": "chet_tillari",
    "military_rank": "harbiy_unvoni",
    "state_awards": "mukofotlari",
    "department_awards": "idoriy_mukofotlari",
    "deputy_info": "deputatligi",
    "current_position_year": "hozirgi_yil",
    "current_position": "hozirgi_ish",
    "photo": "photo",
}

REL_MATCHERS: list[tuple[str, str]] = [
    ("otasi", "ota"),
    ("otas", "ota"),
    ("father", "ota"),
    ("onasi", "ona"),
    ("onas", "ona"),
    ("mother", "ona"),
    ("opasi", "opa"),
    ("opas", "opa"),
    ("singlisi", "singil"),
    ("singli", "singil"),
    ("singil", "singil"),
    ("sister", "singil"),
    ("akasi", "aka"),
    ("akas", "aka"),
    ("ukasi", "uka"),
    ("ukas", "uka"),
    ("brother", "uka"),
    ("turmush", "turmush_ortogi"),
    ("xotin", "turmush_ortogi"),
    ("wife", "turmush_ortogi"),
    ("eri", "turmush_ortogi"),
    ("husband", "turmush_ortogi"),
    ("qaynota", "qaynota"),
    ("qaynona", "qaynona"),
    ("o'g'il", "child"),
    ("ogil", "child"),
    ("qizi", "child"),
    ("farzand", "child"),
    ("son", "child"),
    ("daughter", "child"),
]


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _none(lang: str) -> str:
    return NONE_CYR if lang == "uz_cyr" else NONE_UZ


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


def _val(value: str, *, none: str) -> str:
    lang = "uz_cyr" if none == NONE_CYR else "uz_lat"
    return field_or_none(value, lang)


def _norm_degree(s: str) -> str:
    return s.lower().replace("'", "'").replace("ʻ", "'").strip()


def _rel_bucket(degree: str) -> str | None:
    d = _norm_degree(degree)
    for key, bucket in REL_MATCHERS:
        if key in d:
            return bucket
    return None


def _rel_cells(rel: dict[str, Any] | None, *, none: str) -> dict[str, str]:
    if not rel:
        return {"": "", "_yil": "", "_ish": "", "_tur": ""}
    return {
        "": _val(_to_text(rel.get("fullname") or rel.get("name")), none=none),
        "_yil": _val(_to_text(rel.get("birth_year_place") or rel.get("birth")), none=none),
        "_ish": _val(_to_text(rel.get("work_place") or rel.get("job")), none=none),
        "_tur": _val(_to_text(rel.get("address") or rel.get("addr")), none=none),
    }


def build_objective_data(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Form / DB / API → canonical objective payload.
    All renderers (preview PDF, demo PDF, paid DOCX) must use this function only.
    """
    lang = _to_text(raw.get("lang")) or "uz_lat"
    none = _none(lang)
    L = labels_for(lang)

    mdata = build_malumotnoma_data(raw)
    current_job = mdata["current_job"]
    current_job_year = mdata["current_job_year"]
    work_lines = mdata["work_lines"]

    relatives = _parse_list(raw.get("relatives") or raw.get("rels"))
    rel_rows: list[dict[str, str]] = []
    for rel in relatives:
        rel_rows.append(
            {
                "relationship": _to_text(rel.get("degree") or rel.get("type")),
                "full_name": _val(_to_text(rel.get("fullname") or rel.get("name")), none=none),
                "birth_info": _val(
                    _to_text(rel.get("birth_year_place") or rel.get("birth")), none=none
                ),
                "work_place": _val(_to_text(rel.get("work_place") or rel.get("job")), none=none),
                "residence": _val(_to_text(rel.get("address") or rel.get("addr")), none=none),
            }
        )

    return {
        "lang": lang,
        "full_name": _to_text(raw.get("fullname")),
        "birth_date": _val(_to_text(raw.get("birthdate") or raw.get("birth")), none=none),
        "birth_place": _val(_to_text(raw.get("birthplace") or raw.get("place")), none=none),
        "nationality": _val(_to_text(raw.get("nation")), none=none),
        "party_membership": _val(_to_text(raw.get("party")), none=none),
        "education": _val(_to_text(raw.get("education") or raw.get("edu")), none=none),
        "graduated_university": _val(_to_text(raw.get("graduated") or raw.get("grad")), none=none),
        "speciality": _val(_to_text(raw.get("specialty") or raw.get("spec")), none=none),
        "academic_degree": _val(_to_text(raw.get("degree") or raw.get("deg")), none=none),
        "academic_title": _val(_to_text(raw.get("scientific_title") or raw.get("ttl")), none=none),
        "languages": _val(_to_text(raw.get("languages") or raw.get("langs")), none=none),
        "military_rank": _val(_to_text(raw.get("military_rank") or raw.get("mil")), none=none),
        "state_awards": _val(_to_text(raw.get("awards") or raw.get("award")), none=none),
        "department_awards": _val(
            _to_text(raw.get("departmental_awards") or raw.get("idor_awards") or raw.get("idor")),
            none=none,
        ),
        "deputy_info": _val(_to_text(raw.get("deputy") or raw.get("dep")), none=none),
        "current_position": current_job or "",
        "current_position_year": current_job_year or "",
        "work_history": work_lines,
        "relatives_table": rel_rows,
        "photo": L["photo_hint"],
    }


def objective_to_template_context(objective: dict[str, Any]) -> dict[str, str]:
    """Map canonical objective data → master template placeholder keys."""
    lang = _to_text(objective.get("lang")) or "uz_lat"
    none = _none(lang)
    work_lines = objective.get("work_history") or []

    ctx: dict[str, str] = {
        TEMPLATE_KEY_MAP["full_name"]: _to_text(objective.get("full_name")),
        TEMPLATE_KEY_MAP["birth_date"]: _to_text(objective.get("birth_date")),
        TEMPLATE_KEY_MAP["birth_place"]: _to_text(objective.get("birth_place")),
        TEMPLATE_KEY_MAP["nationality"]: _to_text(objective.get("nationality")),
        TEMPLATE_KEY_MAP["party_membership"]: _to_text(objective.get("party_membership")),
        TEMPLATE_KEY_MAP["education"]: _to_text(objective.get("education")),
        TEMPLATE_KEY_MAP["graduated_university"]: _to_text(objective.get("graduated_university")),
        TEMPLATE_KEY_MAP["speciality"]: _to_text(objective.get("speciality")),
        TEMPLATE_KEY_MAP["academic_degree"]: _to_text(objective.get("academic_degree")),
        TEMPLATE_KEY_MAP["academic_title"]: _to_text(objective.get("academic_title")),
        TEMPLATE_KEY_MAP["languages"]: _to_text(objective.get("languages")),
        TEMPLATE_KEY_MAP["military_rank"]: _to_text(objective.get("military_rank")),
        TEMPLATE_KEY_MAP["state_awards"]: _to_text(objective.get("state_awards")),
        TEMPLATE_KEY_MAP["department_awards"]: _to_text(objective.get("department_awards")),
        TEMPLATE_KEY_MAP["deputy_info"]: _to_text(objective.get("deputy_info")),
        TEMPLATE_KEY_MAP["current_position_year"]: _to_text(objective.get("current_position_year")),
        TEMPLATE_KEY_MAP["current_position"]: _to_text(objective.get("current_position")),
        TEMPLATE_KEY_MAP["photo"]: _to_text(objective.get("photo")),
        "mehnat_faoliyati": work_lines[0] if len(work_lines) > 0 else none,
    }

    for i in range(2, 9):
        key = f"mehnat_faoliyati_{i}"
        ctx[key] = work_lines[i - 1] if len(work_lines) >= i else ""

    relatives = _parse_list(objective.get("relatives_raw"))
    if not relatives and objective.get("relatives_table"):
        for row in objective["relatives_table"]:
            if not isinstance(row, dict):
                continue
            relatives.append(
                {
                    "degree": row.get("relationship", ""),
                    "fullname": row.get("full_name", ""),
                    "birth_year_place": row.get("birth_info", ""),
                    "work_place": row.get("work_place", ""),
                    "address": row.get("residence", ""),
                }
            )

    buckets: dict[str, list[dict[str, Any]]] = {
        "ota": [],
        "ona": [],
        "opa": [],
        "singil": [],
        "uka": [],
        "aka": [],
        "turmush_ortogi": [],
        "child": [],
        "qaynota": [],
        "qaynona": [],
    }
    uka_count = 0
    for rel in relatives:
        degree = _to_text(rel.get("degree") or rel.get("type"))
        bucket = _rel_bucket(degree)
        if bucket == "uka":
            bucket = "uka" if uka_count == 0 else "aka"
            uka_count += 1
        if bucket and bucket in buckets:
            buckets[bucket].append(rel)

    def set_rel(prefix: str, rel: dict[str, Any] | None) -> None:
        cells = _rel_cells(rel, none=none)
        for suffix, val in cells.items():
            ctx[f"{prefix}{suffix}"] = val

    set_rel("ota", buckets["ota"][0] if buckets["ota"] else None)
    set_rel("ona", buckets["ona"][0] if buckets["ona"] else None)
    set_rel("opa", buckets["opa"][0] if buckets["opa"] else None)
    set_rel("singil", buckets["singil"][0] if buckets["singil"] else None)
    set_rel("uka", buckets["uka"][0] if buckets["uka"] else None)
    set_rel("aka", buckets["aka"][0] if buckets["aka"] else None)
    set_rel("turmush_ortogi", buckets["turmush_ortogi"][0] if buckets["turmush_ortogi"] else None)
    set_rel("qaynota", buckets["qaynota"][0] if buckets["qaynota"] else None)
    set_rel("qaynona", buckets["qaynona"][0] if buckets["qaynona"] else None)

    children = buckets["child"]
    child_slots = [
        "farzandlar",
        "farzandlar_2",
        "farzandlar_3",
        "farzandlar_4",
        "farzandlar_5",
        "farzandlar_6",
    ]
    for slot, rel in zip(child_slots, children):
        set_rel(slot, rel)
    for slot in child_slots[len(children) :]:
        set_rel(slot, None)

    template_keys = [
        "ota", "ota_yil", "ota_ish", "ota_tur",
        "ona", "ona_yil", "ona_ish", "ona_tur",
        "opa", "opa_yil", "opa_ish", "opa_tur",
        "singil", "singil_yil", "singil_ish", "singil_tur",
        "uka", "uka_yil", "uka_ish", "uka_tur",
        "aka", "aka_yil", "aka_ish", "aka_tur",
        "turmush_ortogi", "turmush_ortogi_yil", "turmush_ortogi_ish", "turmush_ortogi_tur",
        "farzandlar", "farzandlar_yil", "farzandlar_ish", "farzandlar_tur",
        "farzandlar_2", "farzandlar_2_yil", "farzandlar_2_ish", "farzandlar_2_tur",
        "farzandlar_3", "farzandlar_3_yil", "farzandlar_3_ish", "farzandlar_3_tur",
        "farzandlar_4", "farzandlar_4_yil", "farzandlar_4_ish", "farzandlar_4_tur",
        "farzandlar_5", "farzandlar_5_yil", "farzandlar_5_ish", "farzandlar_5_tur",
        "farzandlar_6", "farzandlar_6_yil", "farzandlar_6_ish", "farzandlar_6_tur",
        "qaynota", "qaynota_yil", "qaynota_ish", "qaynota_tur",
        "qaynona", "qaynona_yil", "qaynona_ish", "qaynona_tur",
    ]
    for k in template_keys:
        ctx.setdefault(k, "")

    return ctx


def buildObjectiveData(raw: dict[str, Any]) -> dict[str, Any]:
    """JS / API naming parity."""
    return build_objective_data(raw)


def build_placeholder_context(raw: dict[str, Any]) -> dict[str, str]:
    """Master template render context — always via build_objective_data."""
    objective = build_objective_data(raw)
    relatives_raw = _parse_list(raw.get("relatives") or raw.get("rels"))
    objective["relatives_raw"] = relatives_raw
    ctx = objective_to_template_context(objective)
    if relatives_raw:
        ctx["_has_relatives"] = "1"
    return ctx
