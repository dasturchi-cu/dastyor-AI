"""Reference font sizes — «Намуна Объективка (18).doc» (DOCX audit)."""

from __future__ import annotations

import re
from typing import Iterable

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"
VAL = f"{{{W_NS}}}val"

# Reference hierarchy (half-points = pt * 2)
SZ_TITLE = 28  # 14 pt — MA'LUMOTNOMA, F.I.Sh, MEHNAT FAOLIYATI
SZ_REL_LINE = 24  # 12 pt — «…ning yaqin qarindoshlari haqida», MA'LUMOT (p2)
SZ_BODY = 22  # 11 pt — body, work history, family table
SZ_PHOTO = 20  # 10 pt — photo hint (reference)
SZ_PHOTO_NOTE = 18  # 9 pt — «(rasmiy kiyimda).» fragment in reference

ALLOWED_FONT_PTS = (9.0, 10.0, 11.0, 12.0, 14.0)

from features.obyektivka.docx_annotations import (
    GARBAGE_EXACT,
    is_garbage_run,
    strip_reference_annotations,
)


def _run_text(r_el: etree._Element) -> str:
    return "".join(t.text or "" for t in r_el.findall(f".//{W}t"))


def _paragraph_text(p_el: etree._Element) -> str:
    return "".join(t.text or "" for t in p_el.findall(f".//{W}t")).strip()


def _in_table(el: etree._Element) -> bool:
    p = el
    while p is not None:
        if p.tag == f"{W}tbl":
            return True
        p = p.getparent()
    return False


def _r_pr(r_el: etree._Element) -> etree._Element:
    rpr = r_el.find(f"{W}rPr")
    if rpr is None:
        rpr = etree.Element(f"{W}rPr")
        r_el.insert(0, rpr)
    return rpr


def _set_sz(rpr: etree._Element, half_points: int) -> None:
    for tag in ("sz", "szCs"):
        for el in rpr.findall(f"{W}{tag}"):
            rpr.remove(el)
        el = etree.SubElement(rpr, f"{W}{tag}")
        el.set(VAL, str(half_points))


def _set_bool(rpr: etree._Element, tag: str, on: bool) -> None:
    for el in rpr.findall(f"{W}{tag}"):
        rpr.remove(el)
    el = etree.SubElement(rpr, f"{W}{tag}")
    if not on:
        el.set(VAL, "0")


def _set_paragraph_runs_sz(p_el: etree._Element, half_points: int, *, bold: bool | None = None) -> None:
    for r_el in p_el.findall(f".//{W}r"):
        rpr = _r_pr(r_el)
        _set_sz(rpr, half_points)
        if bold is not None:
            _set_bool(rpr, "b", bold)
            _set_bool(rpr, "bCs", bold)


def _is_photo_hint_paragraph(text: str) -> bool:
    low = text.lower()
    return any(
        k in low
        for k in (
            "3х4",
            "3x4",
            "фотосурат",
            "fotosurat",
            "расмий кийимда",
            "{{photo}}",
            "oq fondagi",
            "оқ фондаги",
        )
    )


def _is_relatives_intro(text: str) -> bool:
    return "қариндошлари ҳақида" in text or "qarindoshlari haqida" in text.lower()


def _is_fish_name_line(text: str, fish: str) -> bool:
    t = text.strip()
    if not t or _is_relatives_intro(t):
        return False
    if fish and t == fish.strip():
        return True
    if t == "{{fish}}":
        return True
    return False


def enforce_reference_fonts(root: etree._Element, context: dict[str, str] | None = None) -> None:
    """Apply reference font sizes after placeholder fill."""
    ctx = context or {}
    fish = (ctx.get("fish") or "").strip()
    strip_reference_annotations(root)

    for p_el in root.findall(f".//{W}p"):
        if _in_table(p_el):
            continue
        text = _paragraph_text(p_el)
        if not text:
            continue

        if "МАЪЛУМОТНОМА" in text or "MA'LUMOTNOMA" in text:
            _set_paragraph_runs_sz(p_el, SZ_TITLE)
            continue

        if text in ("МАЪЛУМОТ", "MA'LUMOT"):
            _set_paragraph_runs_sz(p_el, SZ_REL_LINE, bold=True)
            continue

        if "МЕҲНАТ ФАОЛИЯТИ" in text or "MEHNAT FAOLIYATI" in text:
            _set_paragraph_runs_sz(p_el, SZ_TITLE, bold=True)
            continue

        if _is_relatives_intro(text):
            _set_paragraph_runs_sz(p_el, SZ_REL_LINE, bold=True)
            continue

        if _is_fish_name_line(text, fish):
            _set_paragraph_runs_sz(p_el, SZ_TITLE, bold=True)
            continue

        if _is_photo_hint_paragraph(text):
            for r_el in p_el.findall(f".//{W}r"):
                t = _run_text(r_el).strip()
                if t in {"(расмий кийимда).", "(rasmiy kiyimda)."}:
                    _set_sz(_r_pr(r_el), SZ_PHOTO_NOTE)
                else:
                    _set_sz(_r_pr(r_el), SZ_PHOTO)
            continue

        # Body rows, current job, work history placeholders/lines
        _set_paragraph_runs_sz(p_el, SZ_BODY)

    # Family table — reference: 11 pt all cells
    for tc in root.findall(f".//{W}tc"):
        for p_el in tc.findall(f".//{W}p"):
            _set_paragraph_runs_sz(p_el, SZ_BODY)
        first_p = tc.find(f".//{W}p")
        if first_p is None:
            continue
        label = _paragraph_text(first_p)
        if not label or label.startswith("{{") or "Фамилияси" in label or "Қариндош" in label:
            continue
        for r_el in first_p.findall(f".//{W}r"):
            rpr = _r_pr(r_el)
            _set_bool(rpr, "b", True)
            _set_bool(rpr, "bCs", True)


def effective_sz_pt(r_el: etree._Element) -> float | None:
    rpr = r_el.find(f"{W}rPr")
    if rpr is None:
        return None
    sz = rpr.find(f"{W}sz")
    if sz is None:
        return None
    try:
        return int(sz.get(VAL)) / 2
    except (TypeError, ValueError):
        return None


def collect_font_sizes(root: etree._Element) -> dict[float, int]:
    from collections import Counter

    c: Counter[float] = Counter()
    for r_el in root.findall(f".//{W}r"):
        text = _run_text(r_el).strip()
        if not text or is_garbage_run(text):
            continue
        pt = effective_sz_pt(r_el)
        if pt is not None:
            c[pt] += 1
    return dict(c)


def disallowed_sizes(sizes: dict[float, int]) -> list[float]:
    allowed = set(ALLOWED_FONT_PTS)
    return sorted(pt for pt in sizes if pt not in allowed)
