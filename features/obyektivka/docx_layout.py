"""Obyektivka DOCX layout — spacing, current job block, table density."""

from __future__ import annotations

import re
from typing import Any

from lxml import etree

from features.obyektivka.docx_typography import (
    W,
    VAL,
    _is_bold_run,
    _run_text,
    _r_pr,
    _set_bool,
    _set_underline,
    apply_current_job_rpr,
    apply_label_rpr,
    apply_plain_value_rpr,
    apply_value_rpr,
)


def _paragraph_text(p_el: etree._Element) -> str:
    return "".join(t.text or "" for t in p_el.findall(f".//{W}t")).strip()

# Twentieths of a point (Word spacing units) — .env: OBY_DOCX_*_TWIPS
from features.obyektivka.spacing_config import (
    DOCX_AFTER_FISH_TWIPS,
    DOCX_GRID_BEFORE_TWIPS,
    DOCX_MEHNAT_BEFORE_TWIPS,
)

SP_AFTER_FISH = DOCX_AFTER_FISH_TWIPS
SP_AFTER_CURRENT_YEAR = 40  # 2 pt — sana va lavozim orasi
SP_BEFORE_CURRENT_JOB = 0
SP_WORK_LINE_BEFORE = DOCX_MEHNAT_BEFORE_TWIPS
SP_WORK_LINE_AFTER = 0
SP_WORK_LINE_HEIGHT = 276  # 1.15 interval
SP_TABLE_LINE = 276

_CURRENT_YEAR_RE = re.compile(
    r"(yildan|йилдан|октябрдан|oktabrdan|январдан|yanvardan)\s*:?\s*$",
    re.IGNORECASE,
)
_WORK_LINE_RE = re.compile(
    r"^\d{4}|\d{4}-\d{4}|йй\.|yy\.|й\.\s*-\s*ҳ\.в|h\.v",
    re.IGNORECASE,
)


def _p_pr(p_el: etree._Element) -> etree._Element:
    ppr = p_el.find(f"{W}pPr")
    if ppr is None:
        ppr = etree.Element(f"{W}pPr")
        p_el.insert(0, ppr)
    return ppr


def _set_spacing(
    ppr: etree._Element,
    *,
    before: int | None = None,
    after: int | None = None,
    line: int | None = None,
    line_rule: str | None = None,
) -> None:
    sp = ppr.find(f"{W}spacing")
    if sp is None:
        sp = etree.SubElement(ppr, f"{W}spacing")
    if before is not None:
        sp.set(f"{W}before", str(before))
    if after is not None:
        sp.set(f"{W}after", str(after))
    if line is not None:
        sp.set(f"{W}line", str(line))
    if line_rule is not None:
        sp.set(f"{W}lineRule", line_rule)


def _in_table(el: etree._Element) -> bool:
    p = el
    while p is not None:
        if p.tag == f"{W}tbl":
            return True
        p = p.getparent()
    return False


def _is_fish_paragraph(text: str, fish: str) -> bool:
    t = text.strip()
    if not t:
        return False
    if fish and t == fish.strip():
        return True
    return t == "{{fish}}"


def _is_mehnat_header(text: str) -> bool:
    return "МЕҲНАТ ФАОЛИЯТИ" in text or "MEHNAT FAOLIYATI" in text


def _is_work_line(text: str) -> bool:
    t = text.strip()
    if not t or _is_mehnat_header(t):
        return False
    if t in ("yo'q", "йўқ"):
        return True
    return bool(_WORK_LINE_RE.search(t))


def _is_current_year_line(text: str) -> bool:
    return bool(_CURRENT_YEAR_RE.search(text.strip()))


def _style_fish_paragraph(p_el: etree._Element) -> None:
    ppr = _p_pr(p_el)
    jc = ppr.find(f"{W}jc")
    if jc is None:
        jc = etree.SubElement(ppr, f"{W}jc")
    jc.set(VAL, "center")
    _set_spacing(ppr, after=SP_AFTER_FISH)
    for r_el in p_el.findall(f".//{W}r"):
        if not _run_text(r_el).strip():
            continue
        rpr = _r_pr(r_el)
        _set_bool(rpr, "b", True)
        _set_bool(rpr, "bCs", True)
        _set_underline(rpr, False)


_NONE_VALUES = frozenset({"yo'q", "йўқ", ""})


def _norm_job_text(text: str) -> str:
    return text.strip().rstrip(":")


def _is_current_job_year_paragraph(text: str, year: str) -> bool:
    t = _norm_job_text(text)
    y = _norm_job_text(year)
    if not t:
        return False
    if y and t == y:
        return True
    return bool(_CURRENT_YEAR_RE.search(t))


def _is_current_job_title_paragraph(text: str, job: str) -> bool:
    t = text.strip()
    j = job.strip()
    if not t or not j:
        return False
    if t == j:
        return True
    return False


def _style_current_job_block(body: etree._Element, ctx: dict[str, str]) -> int:
    """Namuna: ism → ochiq joy → sana qatori → lavozim (qalin, chiziqli)."""
    year = (ctx.get("hozirgi_yil") or "").strip()
    job = (ctx.get("hozirgi_ish") or "").strip()
    if not job or job in _NONE_VALUES:
        _remove_empty_current_job_paragraphs(body, (ctx.get("fish") or "").strip())
        return 0

    paragraphs = body.findall(f"{W}p")
    styled = 0
    year_idx: int | None = None
    job_idx: int | None = None

    for i, p_el in enumerate(paragraphs):
        if _in_table(p_el):
            continue
        text = _paragraph_text(p_el)
        if not text:
            continue
        if _is_mehnat_header(text):
            break
        if year and _is_current_job_year_paragraph(text, year):
            year_idx = i
        if _is_current_job_title_paragraph(text, job):
            job_idx = i

    if year_idx is None and job_idx is None:
        return 0

    if year_idx is not None:
        p_year = paragraphs[year_idx]
        ppr = _p_pr(p_year)
        _set_spacing(
            ppr,
            before=SP_BEFORE_CURRENT_JOB,
            after=SP_AFTER_CURRENT_YEAR,
            line=SP_WORK_LINE_HEIGHT,
        )
        for r_el in p_year.findall(f".//{W}r"):
            if _run_text(r_el).strip():
                apply_value_rpr(r_el)
        styled += 1

    if job_idx is not None:
        p_job = paragraphs[job_idx]
        ppr = _p_pr(p_job)
        _set_spacing(
            ppr,
            before=0 if year_idx is not None else SP_BEFORE_CURRENT_JOB,
            after=SP_AFTER_FISH // 3,
            line=SP_WORK_LINE_HEIGHT,
        )
        for r_el in p_job.findall(f".//{W}r"):
            if _run_text(r_el).strip():
                apply_current_job_rpr(r_el)
        styled += 1

    return styled


def _remove_empty_current_job_paragraphs(body: etree._Element, fish: str = "") -> None:
    """Hozirgi ish bo'lmasa — ism tagidagi bo'sh qatorlarni olib tashlash."""
    paragraphs = body.findall(f"{W}p")
    fish_seen = False
    to_remove: list[etree._Element] = []
    for p_el in paragraphs:
        if _in_table(p_el):
            continue
        text = _paragraph_text(p_el)
        if _is_fish_paragraph(text, fish):
            fish_seen = True
            continue
        if not fish_seen:
            continue
        if _is_mehnat_header(text):
            break
        if not text:
            to_remove.append(p_el)
    for p_el in to_remove:
        body.remove(p_el)


def _fix_work_history_spacing(body: etree._Element) -> None:
    in_mehnat = False
    first_work = True
    for p_el in body.findall(f"{W}p"):
        if _in_table(p_el):
            continue
        text = _paragraph_text(p_el)
        if not text:
            continue
        if _is_mehnat_header(text):
            in_mehnat = True
            first_work = True
            continue
        if not in_mehnat:
            continue
        if not _is_work_line(text):
            in_mehnat = False
            continue
        ppr = _p_pr(p_el)
        before = SP_WORK_LINE_BEFORE if first_work else 0
        _set_spacing(
            ppr,
            before=before,
            after=SP_WORK_LINE_AFTER,
            line=SP_WORK_LINE_HEIGHT,
            line_rule="auto",
        )
        first_work = False
        for r_el in p_el.findall(f".//{W}r"):
            if not _run_text(r_el).strip():
                continue
            apply_plain_value_rpr(r_el)


def _is_relatives_table(tbl: etree._Element) -> bool:
    text_blob = _paragraph_text(tbl)
    norm = text_blob.casefold().replace("-", "").replace("\u2011", "")
    return (
        "qarindosh" in norm
        or "қариндош" in norm
        or "турар жойи" in norm
        or "turar joyi" in norm
    )


def _apply_rel_table_column_widths(tbl: etree._Element, cols: tuple[int, ...], total: int) -> None:
    tbl_grid = tbl.find(f"{W}tblGrid")
    if tbl_grid is not None:
        grid_cols = tbl_grid.findall(f"{W}gridCol")
        for gc, w in zip(grid_cols, cols):
            gc.set(f"{W}w", str(w))
    for tr in tbl.findall(f"{W}tr"):
        col_idx = 0
        for tc in tr.findall(f"{W}tc"):
            tc_pr = tc.find(f"{W}tcPr")
            if tc_pr is None:
                tc_pr = etree.Element(f"{W}tcPr")
                tc.insert(0, tc_pr)
            span_el = tc_pr.find(f"{W}gridSpan")
            span = 1
            if span_el is not None:
                try:
                    span = max(1, int(span_el.get(VAL) or 1))
                except (TypeError, ValueError):
                    span = 1
            tc_w = tc_pr.find(f"{W}tcW")
            if tc_w is None:
                tc_w = etree.SubElement(tc_pr, f"{W}tcW")
            tc_w.set(VAL, "dxa")
            width = sum(cols[col_idx : col_idx + span]) if col_idx < len(cols) else total
            tc_w.set(f"{W}w", str(width))
            col_idx += span


def _fix_relatives_table(root: etree._Element) -> None:
    from features.obyektivka.layout import REL_TABLE_WIDTH_DXA, scaled_rel_col_dxa

    cols = scaled_rel_col_dxa()
    rel_total = str(REL_TABLE_WIDTH_DXA)
    for tbl in root.findall(f".//{W}tbl"):
        if not _is_relatives_table(tbl):
            continue
        tbl_pr = tbl.find(f"{W}tblPr")
        if tbl_pr is None:
            tbl_pr = etree.Element(f"{W}tblPr")
            tbl.insert(0, tbl_pr)
        jc = tbl_pr.find(f"{W}jc")
        if jc is None:
            jc = etree.SubElement(tbl_pr, f"{W}jc")
        jc.set(VAL, "center")
        for ind in list(tbl_pr.findall(f"{W}tblInd")):
            tbl_pr.remove(ind)
        tw = tbl_pr.find(f"{W}tblW")
        if tw is None:
            tw = etree.SubElement(tbl_pr, f"{W}tblW")
        tw.set(VAL, "dxa")
        tw.set(f"{W}w", rel_total)
        _apply_rel_table_column_widths(tbl, cols, REL_TABLE_WIDTH_DXA)
        rows = tbl.findall(f"{W}tr")
        for ri, tr in enumerate(rows):
            tr_pr = tr.find(f"{W}trPr")
            if tr_pr is not None:
                for h in tr_pr.findall(f"{W}trHeight"):
                    tr_pr.remove(h)
            for ci, tc in enumerate(tr.findall(f"{W}tc")):
                tc_pr = tc.find(f"{W}tcPr")
                if tc_pr is not None:
                    for shd in tc_pr.findall(f"{W}shd"):
                        shd.set(VAL, "clear")
                        shd.set(f"{W}color", "auto")
                        shd.set(f"{W}fill", "FFFFFF")
                    mar = tc_pr.find(f"{W}tcMar")
                    if mar is None:
                        mar = etree.SubElement(tc_pr, f"{W}tcMar")
                    for side in ("top", "bottom"):
                        el = mar.find(f"{W}{side}")
                        if el is None:
                            el = etree.SubElement(mar, f"{W}{side}")
                        el.set(VAL, "0")
                        el.set(f"{W}type", "dxa")
                for p_el in tc.findall(f".//{W}p"):
                    ppr = _p_pr(p_el)
                    _set_spacing(ppr, before=0, after=0, line=SP_TABLE_LINE, line_rule="auto")
                    for r_el in p_el.findall(f".//{W}r"):
                        if not _run_text(r_el).strip():
                            continue
                        if ri == 0 or ci == 0:
                            apply_label_rpr(r_el)
                        else:
                            apply_plain_value_rpr(r_el)


def _dedupe_cell_none_values(root: etree._Element) -> None:
    """One «yo'q» per empty cell — avoid yo'qyo'q from stacked placeholders."""
    none_pat = re.compile(r"^(yo'q|йўқ)+$", re.IGNORECASE)
    for p_el in root.findall(f".//{W}p"):
        text = _paragraph_text(p_el).replace(" ", "")
        if len(text) <= 4 or not none_pat.match(text):
            continue
        word = "йўқ" if "йў" in text else "yo'q"
        for r_el in list(p_el.findall(f"{W}r")):
            p_el.remove(r_el)
        r_el = etree.SubElement(p_el, f"{W}r")
        t = etree.SubElement(r_el, f"{W}t")
        t.text = word
        apply_plain_value_rpr(r_el)


def enforce_reference_layout(root: etree._Element, context: dict[str, str] | None = None) -> dict[str, Any]:
    ctx = context or {}
    fish = (ctx.get("fish") or "").strip()
    stats: dict[str, Any] = {}

    body = root.find(f"{W}body")
    if body is not None:
        for p_el in body.findall(f"{W}p"):
            if _in_table(p_el):
                continue
            if _is_fish_paragraph(_paragraph_text(p_el), fish):
                _style_fish_paragraph(p_el)
        stats["styled_current_job"] = _style_current_job_block(body, ctx)
        _fix_work_history_spacing(body)

    _fix_relatives_table(root)
    _dedupe_cell_none_values(root)
    return stats
