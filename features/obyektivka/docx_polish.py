"""Final PPT/reference polish — black text, Times New Roman, alignment, spacing."""

from __future__ import annotations

import re

from lxml import etree

from features.obyektivka.docx_typography import (
    W,
    VAL,
    _paragraph_text,
    _r_pr,
    _run_text,
    _set_bool,
    _set_color_black,
    _set_underline,
    apply_label_rpr,
    apply_value_rpr,
)

FONT_TIMES = "Times New Roman"

# PPT spec: 8 pt before = 160 twips; 4 pt = 80; line 1.15 = 276 (240 * 1.15)
SP_LINE_115 = 276
SP_GRID_BEFORE = 160
SP_MEHNAT_BEFORE = 80
SP_TITLE_AFTER = 120

_CURRENT_YEAR_RE = re.compile(
    r"(yildan|йилдан|октябрдан|oktabrdan|январдан|yanvardan)\s*:?\s*$",
    re.IGNORECASE,
)
_GRID_LABEL_RE = re.compile(
    r"(Туғилган йили|Tug'ilgan yili|Туғилган жойи|Tug'ilgan joyi)",
    re.IGNORECASE,
)


def _is_current_job_year(text: str, year: str) -> bool:
    t = text.strip().rstrip(":")
    y = year.strip().rstrip(":")
    if y and t == y:
        return True
    return bool(_CURRENT_YEAR_RE.search(text.strip()))


def _is_current_job_title(text: str, job: str) -> bool:
    return bool(job.strip() and text.strip() == job.strip())


def _in_table(el: etree._Element) -> bool:
    p = el
    while p is not None:
        if p.tag == f"{W}tbl":
            return True
        p = p.getparent()
    return False


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


def _set_jc(ppr: etree._Element, align: str) -> None:
    jc = ppr.find(f"{W}jc")
    if jc is None:
        jc = etree.SubElement(ppr, f"{W}jc")
    jc.set(VAL, align)


def _set_rfonts(rpr: etree._Element, name: str = FONT_TIMES) -> None:
    for el in rpr.findall(f"{W}rFonts"):
        rpr.remove(el)
    rf = etree.SubElement(rpr, f"{W}rFonts")
    rf.set(f"{W}ascii", name)
    rf.set(f"{W}hAnsi", name)
    rf.set(f"{W}cs", name)
    rf.set(f"{W}eastAsia", name)


def _is_malumotnoma(text: str) -> bool:
    return "МАЪЛУМОТНОМА" in text or "MA'LUMOTNOMA" in text


def _is_mehnat_header(text: str) -> bool:
    return "МЕҲНАТ ФАОЛИЯТИ" in text or "MEHNAT FAOLIYATI" in text


def _is_relatives_intro(text: str) -> bool:
    return "қариндошлари ҳақида" in text or "qarindoshlari haqida" in text.lower()


def _is_label_paragraph(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    if _is_malumotnoma(t) or _is_mehnat_header(t) or _is_relatives_intro(t):
        return False
    if t.endswith(":") or ": " in t:
        return True
    return any(
        k in t
        for k in (
            "Туғилган йили",
            "Туғилган жойи",
            "Миллати",
            "Партиявийлиги",
            "Маълумоти",
            "Тамомлаган",
            "Илмий даражаси",
            "Илмий унвони",
            "Давлат мукофот",
            "Идоравий мукофот",
            "Халқ депутат",
            "сайланadigan",
            "сайланадиган",
        )
    )


def enforce_reference_polish(root: etree._Element, context: dict[str, str] | None = None) -> None:
    """PPT namuna: qora harf, Times New Roman, sarlavha markazda, 1.15 interval."""
    ctx = context or {}
    fish = (ctx.get("fish") or "").strip()
    hozirgi_yil = (ctx.get("hozirgi_yil") or "").strip()
    hozirgi_ish = (ctx.get("hozirgi_ish") or "").strip()

    for r_el in root.findall(f".//{W}r"):
        if not _run_text(r_el).strip():
            continue
        rpr = _r_pr(r_el)
        _set_rfonts(rpr)
        _set_color_black(rpr)

    body = root.find(f"{W}body")
    if body is None:
        return

    grid_marked = False
    for p_el in body.findall(f"{W}p"):
        if _in_table(p_el):
            continue
        text = _paragraph_text(p_el)
        if not text:
            continue

        if hozirgi_ish and _is_current_job_title(text, hozirgi_ish):
            continue
        if hozirgi_yil and _is_current_job_year(text, hozirgi_yil):
            for r_el in p_el.findall(f".//{W}r"):
                if _run_text(r_el).strip():
                    apply_value_rpr(r_el)
            continue

        ppr = _p_pr(p_el)
        _set_spacing(ppr, line=SP_LINE_115, line_rule="auto")

        if _is_malumotnoma(text):
            _set_jc(ppr, "center")
            _set_spacing(ppr, line=SP_LINE_115, line_rule="auto", after=SP_TITLE_AFTER)
            for r_el in p_el.findall(f".//{W}r"):
                if _run_text(r_el).strip():
                    apply_label_rpr(r_el)
            continue

        if _is_fish_paragraph(text, fish):
            _set_jc(ppr, "center")
            for r_el in p_el.findall(f".//{W}r"):
                if _run_text(r_el).strip():
                    rpr = _r_pr(r_el)
                    _set_bool(rpr, "b", True)
                    _set_bool(rpr, "bCs", True)
                    _set_underline(rpr, False)
                    _set_color_black(rpr)
            continue

        if _is_mehnat_header(text):
            _set_jc(ppr, "center")
            _set_spacing(ppr, before=SP_MEHNAT_BEFORE, line=SP_LINE_115, line_rule="auto")
            for r_el in p_el.findall(f".//{W}r"):
                if _run_text(r_el).strip():
                    apply_label_rpr(r_el)
            continue

        if _is_relatives_intro(text):
            _set_jc(ppr, "center")
            for r_el in p_el.findall(f".//{W}r"):
                if _run_text(r_el).strip():
                    apply_label_rpr(r_el)
            continue

        if not grid_marked and _GRID_LABEL_RE.search(text):
            _set_spacing(ppr, before=SP_GRID_BEFORE, line=SP_LINE_115, line_rule="auto")
            grid_marked = True

        if _is_label_paragraph(text):
            for r_el in p_el.findall(f".//{W}r"):
                if _run_text(r_el).strip():
                    apply_label_rpr(r_el)
        else:
            for r_el in p_el.findall(f".//{W}r"):
                if _run_text(r_el).strip():
                    apply_value_rpr(r_el)


def _is_fish_paragraph(text: str, fish: str) -> bool:
    t = text.strip()
    if not t:
        return False
    if fish and t == fish.strip():
        return True
    return t == "{{fish}}"
