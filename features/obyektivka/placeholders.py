"""Map WebApp payload → master template placeholder context."""

from __future__ import annotations

import json
import re
from typing import Any

from features.obyektivka.layout import labels_for
from features.obyektivka.malumotnoma_data import build_malumotnoma_data
from features.obyektivka.none_values import field_or_none

NONE_UZ = "yo'q"
NONE_CYR = "йўқ"


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


def _format_work_line(item: dict[str, Any]) -> str:
    year = _to_text(item.get("year") or item.get("years") or item.get("from"))
    end = _to_text(item.get("to"))
    if not year and (item.get("f") or item.get("t")):
        f = _to_text(item.get("f"))
        t = _to_text(item.get("t"))
        year = f"{f}-{t}".strip("-") if f or t else ""
    pos = _to_text(item.get("position") or item.get("desc") or item.get("job") or item.get("d"))
    if year and end and "yy" not in year.lower() and "йй" not in year:
        year = f"{year}-{end}"
    if year and "yy" not in year.lower() and "йй" not in year and year:
        year = f"{year} yy."
    year = year.replace("yy.", "йй.").replace(" yy", " йй")
    if year and pos:
        return f"{year} - {pos}"
    return year or pos


def _infer_current_job(work_items: list[dict[str, Any]]) -> tuple[str, str, list[dict[str, Any]]]:
    items = [dict(x) for x in work_items]
    for idx, item in enumerate(items):
        year_raw = _to_text(item.get("year") or item.get("from"))
        year_norm = re.sub(r"[\s.\-_/]", "", year_raw.lower())
        is_current = any(
            k in year_norm
            for k in ("hv", "hvgacha", "hozirgacha", "ҳв", "ҳвгача", "ҳозиргача", "present", "current")
        )
        pos = _to_text(item.get("position") or item.get("description") or item.get("job") or item.get("d"))
        if is_current and pos:
            yr = _to_text(item.get("from") or item.get("f"))
            if not yr:
                m = re.search(r"(19|20)\d{2}", year_raw)
                yr = m.group(0) if m else year_raw
            items.pop(idx)
            return pos, yr, items
    return "", "", items


def _norm_degree(s: str) -> str:
    return s.lower().replace("'", "'").replace("ʻ", "'").strip()


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


def _rel_bucket(degree: str) -> str | None:
    d = _norm_degree(degree)
    for key, bucket in REL_MATCHERS:
        if key in d:
            return bucket
    return None


def _rel_cells(rel: dict[str, Any] | None, *, none: str) -> dict[str, str]:
    if not rel:
        return {"": none, "_yil": none, "_ish": none, "_tur": none}
    return {
        "": _val(_to_text(rel.get("fullname") or rel.get("name")), none=none),
        "_yil": _val(_to_text(rel.get("birth_year_place") or rel.get("birth")), none=none),
        "_ish": _val(_to_text(rel.get("work_place") or rel.get("job")), none=none),
        "_tur": _val(_to_text(rel.get("address") or rel.get("addr")), none=none),
    }


def build_placeholder_context(raw: dict[str, Any]) -> dict[str, str]:
    lang = _to_text(raw.get("lang")) or "uz_lat"
    none = _none(lang)
    L = labels_for(lang)

    mdata = build_malumotnoma_data(raw)
    current_job = mdata["current_job"]
    current_job_year = mdata["current_job_year"]
    work_lines = mdata["work_lines"]

    ctx: dict[str, str] = {
        "fish": _val(_to_text(raw.get("fullname")), none=""),
        "tugilgan_sana": _val(_to_text(raw.get("birthdate") or raw.get("birth")), none=none),
        "tugilgan_joy": _val(_to_text(raw.get("birthplace") or raw.get("place")), none=none),
        "millati": _val(_to_text(raw.get("nation")), none=none),
        "malumoti": _val(_to_text(raw.get("education") or raw.get("edu")), none=none),
        "tamomlagan": _val(_to_text(raw.get("graduated") or raw.get("grad")), none=none),
        "mutaxassisligi": _val(_to_text(raw.get("specialty") or raw.get("spec")), none=none),
        "partiyaviyligi": _val(_to_text(raw.get("party")), none=none),
        "ilmiy_darajasi": _val(_to_text(raw.get("degree") or raw.get("deg")), none=none),
        "ilmiy_unvoni": _val(_to_text(raw.get("scientific_title") or raw.get("ttl")), none=none),
        "chet_tillari": _val(_to_text(raw.get("languages") or raw.get("langs")), none=none),
        "harbiy_unvoni": _val(_to_text(raw.get("military_rank") or raw.get("mil")), none=none),
        "mukofotlari": _val(_to_text(raw.get("awards") or raw.get("award")), none=none),
        "idoriy_mukofotlari": _val(
            _to_text(raw.get("departmental_awards") or raw.get("idor_awards") or raw.get("idor")),
            none=none,
        ),
        "deputatligi": _val(_to_text(raw.get("deputy") or raw.get("dep")), none=none),
        "hozirgi_yil": _val(current_job_year, none=""),
        "hozirgi_ish": _val(current_job, none=""),
        "mehnat_faoliyati": work_lines[0] if len(work_lines) > 0 else none,
        "photo": L["photo_hint"],
    }

    for i in range(2, 9):
        key = f"mehnat_faoliyati_{i}"
        ctx[key] = work_lines[i - 1] if len(work_lines) >= i else ""

    relatives = _parse_list(raw.get("relatives") or raw.get("rels"))
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
        ctx.setdefault(k, none if k.endswith(("_yil", "_ish", "_tur")) or k in child_slots else "")

    return ctx
