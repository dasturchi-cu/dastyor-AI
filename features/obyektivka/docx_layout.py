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
    apply_label_rpr,
)


def _paragraph_text(p_el: etree._Element) -> str:
    return "".join(t.text or "" for t in p_el.findall(f".//{W}t")).strip()

# Twentieths of a point (Word spacing units): 4 pt = 80
SP_AFTER_FISH = 360  # ~18 pt gap name → current job (reference open space)
SP_BEFORE_CURRENT_JOB = 0
SP_WORK_LINE_BEFORE = 80  # 4 pt — reference bracket on first work line
SP_WORK_LINE_AFTER = 0
SP_WORK_LINE_HEIGHT = 240  # single spacing
SP_TABLE_LINE = 240

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


def _strip_value_underline(root: etree._Element) -> None:
    for r_el in root.findall(f".//{W}r"):
        if not _run_text(r_el).strip():
            continue
        rpr = _r_pr(r_el)
        _set_underline(rpr, False)
        if not _is_bold_run(r_el):
            _set_bool(rpr, "b", False)
            _set_bool(rpr, "bCs", False)


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


def _merge_current_job_paragraphs(body: etree._Element) -> int:
    """Merge «2024-yildan:» + job title into one paragraph below the name."""
    merged = 0
    paragraphs = body.findall(f"{W}p")
    i = 0
    while i < len(paragraphs) - 1:
        p_year = paragraphs[i]
        p_job = paragraphs[i + 1]
        if _in_table(p_year):
            i += 1
            continue
        year_text = _paragraph_text(p_year)
        job_text = _paragraph_text(p_job)
        if not year_text or not job_text:
            i += 1
            continue
        if not _is_current_year_line(year_text):
            i += 1
            continue
        if _is_mehnat_header(job_text) or _is_work_line(job_text):
            i += 1
            continue

        combined = year_text.rstrip()
        if not combined.endswith(":"):
            combined += ":"
        combined += f" {job_text.strip()}"

        for r_el in list(p_year.findall(f"{W}r")):
            p_year.remove(r_el)
        r_el = etree.SubElement(p_year, f"{W}r")
        t = etree.SubElement(r_el, f"{W}t")
        t.text = combined
        rpr = _r_pr(r_el)
        _set_bool(rpr, "b", True)
        _set_bool(rpr, "bCs", True)
        _set_underline(rpr, False)

        ppr = _p_pr(p_year)
        _set_spacing(ppr, before=SP_BEFORE_CURRENT_JOB, after=SP_AFTER_FISH // 2, line=SP_WORK_LINE_HEIGHT)

        body.remove(p_job)
        paragraphs = body.findall(f"{W}p")
        merged += 1
    return merged


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
            rpr = _r_pr(r_el)
            _set_underline(rpr, False)


def _fix_relatives_table(root: etree._Element) -> None:
    for tbl in root.findall(f".//{W}tbl"):
        text_blob = _paragraph_text(tbl)
        if "qarindosh" not in text_blob.lower() and "қариндош" not in text_blob:
            continue
        for tr in tbl.findall(f"{W}tr"):
            tr_pr = tr.find(f"{W}trPr")
            if tr_pr is not None:
                for h in tr_pr.findall(f"{W}trHeight"):
                    tr_pr.remove(h)
            for tc in tr.findall(f"{W}tc"):
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
                        rpr = _r_pr(r_el)
                        _set_underline(rpr, False)
                        if _is_bold_run(r_el):
                            apply_label_rpr(r_el)


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
        _set_underline(_r_pr(r_el), False)


def enforce_reference_layout(root: etree._Element, context: dict[str, str] | None = None) -> dict[str, Any]:
    ctx = context or {}
    fish = (ctx.get("fish") or "").strip()
    stats: dict[str, Any] = {}

    _strip_value_underline(root)

    body = root.find(f"{W}body")
    if body is not None:
        for p_el in body.findall(f"{W}p"):
            if _in_table(p_el):
                continue
            if _is_fish_paragraph(_paragraph_text(p_el), fish):
                _style_fish_paragraph(p_el)
        stats["merged_current_job"] = _merge_current_job_paragraphs(body)
        _fix_work_history_spacing(body)

    _fix_relatives_table(root)
    _dedupe_cell_none_values(root)
    return stats
