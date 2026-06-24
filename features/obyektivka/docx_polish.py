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
    apply_plain_value_rpr,
    apply_value_rpr,
)

FONT_TIMES = "Times New Roman"

# PPT spec (mm → twips @ 1440/25.4); line 1.15 = 276
SP_LINE_115 = 276
SP_GRID_BEFORE = 454  # 8 mm
SP_MEHNAT_BEFORE = 227  # 4 mm
SP_TITLE_AFTER = 120
PAGE_MARGIN_TOP_BOTTOM_MM = 20
PAGE_MARGIN_LEFT_RIGHT_MM = 18
_MM_TWIPS = 1440 / 25.4

_CURRENT_YEAR_RE = re.compile(
    r"(yildan|йилдан|октябрдан|oktabrdan|январдан|yanvardan)\s*:?\s*$",
    re.IGNORECASE,
)
_GRID_LABEL_RE = re.compile(
    r"(Туғилган йили|Tug'ilgan yili|Туғилган жойи|Tug'ilgan joyi)",
    re.IGNORECASE,
)
_WORK_LINE_RE = re.compile(
    r"^\d{4}|\d{4}-\d{4}|йй\.|yy\.|й\.\s*-\s*ҳ\.в|h\.v",
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


def _is_malumot_line(text: str) -> bool:
    return text.strip() in ("МАЪЛУМОТ", "MA'LUMOT")


def _is_photo_hint(text: str) -> bool:
    low = text.lower()
    return any(
        k in low
        for k in ("3х4", "3x4", "фотосурат", "fotosurat", "расмий кийимда", "rasmiy kiyimda")
    )


def _is_work_line(text: str, *, in_mehnat: bool = False) -> bool:
    t = text.strip()
    if not t or _is_mehnat_header(t):
        return False
    if in_mehnat and t in ("yo'q", "йўқ"):
        return True
    return bool(_WORK_LINE_RE.search(t))


def _is_label_paragraph(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    if _is_malumotnoma(t) or _is_mehnat_header(t) or _is_relatives_intro(t) or _is_malumot_line(t):
        return False
    parts = re.split(r"[\t]", t)
    if any(part.strip().endswith(":") for part in parts):
        return True
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


def _mm_twips(mm: float) -> str:
    return str(int(round(mm * _MM_TWIPS)))


def _enforce_page_margins(root: etree._Element) -> None:
    """Namuna DOCX asimetrik marginlar (master shablon bilan bir xil)."""
    from features.obyektivka.layout import (
        PAGE_MARGIN_BOTTOM_TWIPS,
        PAGE_MARGIN_LEFT_TWIPS,
        PAGE_MARGIN_RIGHT_TWIPS,
        PAGE_MARGIN_TOP_TWIPS,
    )

    for sect in root.findall(f".//{W}sectPr"):
        pg = sect.find(f"{W}pgMar")
        if pg is None:
            pg = etree.SubElement(sect, f"{W}pgMar")
        pg.set(f"{W}top", str(PAGE_MARGIN_TOP_TWIPS))
        pg.set(f"{W}bottom", str(PAGE_MARGIN_BOTTOM_TWIPS))
        pg.set(f"{W}left", str(PAGE_MARGIN_LEFT_TWIPS))
        pg.set(f"{W}right", str(PAGE_MARGIN_RIGHT_TWIPS))


def _relatives_table_blob(tbl: etree._Element) -> str:
    return _paragraph_text(tbl).casefold().replace("-", "").replace("\u2011", "")


def _is_relatives_table(tbl: etree._Element) -> bool:
    norm = _relatives_table_blob(tbl)
    return (
        "qarindosh" in norm
        or "қариндош" in norm
        or "турар жойи" in norm
        or "turar joyi" in norm
    )


def _enforce_table_borders(root: etree._Element) -> None:
    for tbl in root.findall(f".//{W}tbl"):
        if not _is_relatives_table(tbl):
            continue
        tbl_pr = tbl.find(f"{W}tblPr")
        if tbl_pr is None:
            tbl_pr = etree.Element(f"{W}tblPr")
            tbl.insert(0, tbl_pr)
        borders = tbl_pr.find(f"{W}tblBorders")
        if borders is None:
            borders = etree.SubElement(tbl_pr, f"{W}tblBorders")
        for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
            el = borders.find(f"{W}{side}")
            if el is None:
                el = etree.SubElement(borders, f"{W}{side}")
            el.set(VAL, "single")
            el.set(f"{W}sz", "8")
            el.set(f"{W}color", "000000")
            el.set(f"{W}space", "0")


def _enforce_table_cell_styles(root: etree._Element) -> None:
    for tbl in root.findall(f".//{W}tbl"):
        if not _is_relatives_table(tbl):
            continue
        rows = tbl.findall(f"{W}tr")
        for ri, tr in enumerate(rows):
            for ci, tc in enumerate(tr.findall(f"{W}tc")):
                for p_el in tc.findall(f".//{W}p"):
                    for r_el in p_el.findall(f".//{W}r"):
                        if not _run_text(r_el).strip():
                            continue
                        if ri == 0 or ci == 0:
                            apply_label_rpr(r_el)
                        else:
                            apply_plain_value_rpr(r_el)


def _strip_highlights(root: etree._Element) -> None:
    """Shablondagi sariq highlight — oddiy oq fon."""
    for parent in root.findall(f".//{W}rPr") + root.findall(f".//{W}pPr"):
        for hl in parent.findall(f"{W}highlight"):
            parent.remove(hl)
        shd = parent.find(f"{W}shd")
        if shd is not None:
            fill = (shd.get(f"{W}fill") or "").upper()
            if fill in ("FFFF00", "YELLOW", "FFF000", "FFC000"):
                parent.remove(shd)


def enforce_reference_polish(root: etree._Element, context: dict[str, str] | None = None) -> None:
    """PPT namuna: qora harf, Times New Roman, sarlavha markazda, 1.15 interval."""
    _strip_highlights(root)
    ctx = context or {}
    fish = (ctx.get("fish") or "").strip()
    hozirgi_yil = (ctx.get("hozirgi_yil") or "").strip()
    hozirgi_ish = (ctx.get("hozirgi_ish") or "").strip()

    _enforce_page_margins(root)
    _enforce_table_borders(root)
    _enforce_table_cell_styles(root)

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
    in_mehnat = False
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

        if _is_photo_hint(text):
            for r_el in p_el.findall(f".//{W}r"):
                if _run_text(r_el).strip():
                    apply_plain_value_rpr(r_el)
            continue

        if _is_mehnat_header(text):
            in_mehnat = True
            _set_jc(ppr, "center")
            _set_spacing(ppr, before=SP_MEHNAT_BEFORE, line=SP_LINE_115, line_rule="auto")
            for r_el in p_el.findall(f".//{W}r"):
                if _run_text(r_el).strip():
                    apply_label_rpr(r_el)
            continue

        if in_mehnat and _is_work_line(text, in_mehnat=True):
            for r_el in p_el.findall(f".//{W}r"):
                if _run_text(r_el).strip():
                    apply_plain_value_rpr(r_el)
            continue

        if in_mehnat and not _is_work_line(text, in_mehnat=True):
            in_mehnat = False

        if _is_relatives_intro(text):
            _set_jc(ppr, "center")
            for r_el in p_el.findall(f".//{W}r"):
                if _run_text(r_el).strip():
                    apply_plain_value_rpr(r_el)
            continue

        if _is_malumot_line(text):
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
