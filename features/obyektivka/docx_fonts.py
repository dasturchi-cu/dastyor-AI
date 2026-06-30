"""Reference font sizes — «Намуна Объективка (18).doc» (DOCX audit)."""

from __future__ import annotations

from lxml import etree

from features.obyektivka.docx_annotations import (
    GARBAGE_EXACT,
    is_garbage_run,
    strip_reference_annotations,
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"
VAL = f"{{{W_NS}}}val"

# Reference hierarchy (half-points = pt * 2) — PPT namuna
SZ_TITLE = 28  # 14 pt — MA'LUMOTNOMA, F.I.Sh, MEHNAT FAOLIYATI
SZ_REL_LINE = 24  # 12 pt — «…qarindoshlari haqida», MA'LUMOT, jadval
SZ_BODY = 22  # 11 pt — body, work history, form values, photo note
SZ_TABLE = 22  # 11 pt — qarindoshlar jadvali (PPT)
SZ_PHOTO = 22  # 11 pt — photo hint (PPT)
SZ_PHOTO_NOTE = 22  # 11 pt — «(rasmiy kiyimda).» (PPT)

ALLOWED_FONT_PTS = (11.0, 12.0, 14.0)


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
            _set_paragraph_runs_sz(p_el, SZ_TITLE, bold=True)
            continue

        if text in ("МАЪЛУМОТ", "MA'LUMOT"):
            _set_paragraph_runs_sz(p_el, SZ_REL_LINE, bold=True)
            continue

        if "МЕҲНАТ ФАОЛИЯТИ" in text or "MEHNAT FAOLIYATI" in text:
            _set_paragraph_runs_sz(p_el, SZ_TITLE, bold=True)
            continue

        if _is_relatives_intro(text):
            _set_paragraph_runs_sz(p_el, SZ_REL_LINE, bold=False)
            continue

        if _is_fish_name_line(text, fish):
            _set_paragraph_runs_sz(p_el, SZ_TITLE, bold=True)
            continue

        if _is_photo_hint_paragraph(text):
            _set_paragraph_runs_sz(p_el, SZ_PHOTO, bold=False)
            continue

        # Body rows, current job, work history placeholders/lines
        _set_paragraph_runs_sz(p_el, SZ_BODY)

    # Family table — PPT: 12 pt; bold faqat sarlavha + 1-ustun
    for tbl in root.findall(f".//{W}tbl"):
        rows = tbl.findall(f"{W}tr")
        is_rel = _is_relatives_table(tbl)
        table_sz = SZ_TABLE if is_rel else SZ_BODY
        for ri, tr in enumerate(rows):
            for ci, tc in enumerate(tr.findall(f"{W}tc")):
                is_bold = (ri == 0 or ci == 0) if is_rel else None
                for p_el in tc.findall(f".//{W}p"):
                    _set_paragraph_runs_sz(p_el, table_sz, bold=is_bold)


def _is_relatives_table(tbl: etree._Element) -> bool:
    text_blob = _paragraph_text(tbl)
    norm = text_blob.casefold().replace("-", "").replace("\u2011", "")
    return (
        "qarindosh" in norm
        or "қариндош" in norm
        or "турар жойи" in norm
        or "turar joyi" in norm
    )


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
