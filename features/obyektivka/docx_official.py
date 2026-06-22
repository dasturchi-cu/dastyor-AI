"""
Official Obyektivka (Ma'lumotnoma) DOCX generator.
Layout mirrors «Намуна Объективка (18).doc» (tab-based fields, exact margins).
"""

import base64
import json
import logging
import os
import re
from typing import Any

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

from backend.services.document_render.photo import process_passport_photo
from features.obyektivka.layout import (
    FONT_BODY_PT,
    FONT_REL_TITLE_PT,
    FONT_TITLE_PT,
    LINE_HEIGHT,
    PAGE_MARGIN_BOTTOM_MM,
    PAGE_MARGIN_LEFT_MM,
    PAGE_MARGIN_RIGHT_MM,
    PAGE_MARGIN_TOP_MM,
    PHOTO_HEIGHT_MM,
    PHOTO_WIDTH_MM,
    REL_COL_DXA,
    TAB_COL_POS,
    labels_for,
)

logger = logging.getLogger(__name__)


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _parse_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def _set_run_font(run, *, size: int = FONT_BODY_PT, bold: bool | None = None) -> None:
    if bold is not None:
        run.bold = bold
    run.font.size = Pt(size)
    run.font.name = "Times New Roman"


def _set_cell_no_borders(cell) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_borders = tc_pr.find(qn("w:tcBorders"))
    if tc_borders is None:
        tc_borders = OxmlElement("w:tcBorders")
        tc_pr.append(tc_borders)
    for side in ("top", "left", "bottom", "right"):
        border = tc_borders.find(qn(f"w:{side}"))
        if border is None:
            border = OxmlElement(f"w:{side}")
            tc_borders.append(border)
        border.set(qn("w:val"), "none")
        border.set(qn("w:sz"), "0")
        border.set(qn("w:space"), "0")


def _set_table_no_borders_strict(table) -> None:
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    tbl_style = tbl_pr.find(qn("w:tblStyle"))
    if tbl_style is not None:
        tbl_pr.remove(tbl_style)

    tbl_borders = tbl_pr.find(qn("w:tblBorders"))
    if tbl_borders is None:
        tbl_borders = OxmlElement("w:tblBorders")
        tbl_pr.append(tbl_borders)
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        border = tbl_borders.find(qn(f"w:{side}"))
        if border is None:
            border = OxmlElement(f"w:{side}")
            tbl_borders.append(border)
        border.set(qn("w:val"), "none")
        border.set(qn("w:sz"), "0")
        border.set(qn("w:space"), "0")

    tbl_look = tbl_pr.find(qn("w:tblLook"))
    if tbl_look is None:
        tbl_look = OxmlElement("w:tblLook")
        tbl_pr.append(tbl_look)
    tbl_look.set(qn("w:firstRow"), "0")
    tbl_look.set(qn("w:lastRow"), "0")
    tbl_look.set(qn("w:firstColumn"), "0")
    tbl_look.set(qn("w:lastColumn"), "0")
    tbl_look.set(qn("w:noHBand"), "1")
    tbl_look.set(qn("w:noVBand"), "1")

    for row in table.rows:
        for cell in row.cells:
            _set_cell_no_borders(cell)


def _set_table_borders(table, size_pt: float = 1.0) -> None:
    size_eighth_pt = str(int(size_pt * 8))
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    tbl_borders = tbl_pr.find(qn("w:tblBorders"))
    if tbl_borders is None:
        tbl_borders = OxmlElement("w:tblBorders")
        tbl_pr.append(tbl_borders)
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        border = tbl_borders.find(qn(f"w:{side}"))
        if border is None:
            border = OxmlElement(f"w:{side}")
            tbl_borders.append(border)
        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), size_eighth_pt)
        border.set(qn("w:space"), "0")
        border.set(qn("w:color"), "000000")


def _set_col_widths_dxa(table, widths: tuple[int, ...]) -> None:
    tbl = table._tbl
    grid = tbl.find(qn("w:tblGrid"))
    if grid is None:
        grid = OxmlElement("w:tblGrid")
        tbl.insert(0, grid)
    for old in list(grid.findall(qn("w:gridCol"))):
        grid.remove(old)
    for w in widths:
        gc = OxmlElement("w:gridCol")
        gc.set(qn("w:w"), str(w))
        grid.append(gc)
    for row in table.rows:
        for i, cell in enumerate(row.cells):
            if i < len(widths):
                cell.width = widths[i]


def _para_tab(p, before: float = 0, after: float = 0) -> None:
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = LINE_HEIGHT
    p.paragraph_format.tab_stops.add_tab_stop(TAB_COL_POS)


def _add_two_col_pair(
    doc: Document,
    left_label: str,
    left_value: str,
    right_label: str,
    right_value: str,
    *,
    none: str,
) -> None:
    p = doc.add_paragraph()
    _para_tab(p, before=8)
    lr = p.add_run(f"{left_label}:")
    _set_run_font(lr, bold=True)
    p.add_run("\t")
    rr = p.add_run(f"{right_label}:")
    _set_run_font(rr, bold=True)

    p2 = doc.add_paragraph()
    _para_tab(p2)
    v1 = p2.add_run(left_value or none)
    _set_run_font(v1)
    p2.add_run("\t")
    v2 = p2.add_run(right_value or none)
    _set_run_font(v2)


def _add_inline_field(doc: Document, label: str, value: str, *, none: str) -> None:
    p = doc.add_paragraph()
    _para_tab(p, before=8)
    lr = p.add_run(f"{label}:")
    _set_run_font(lr, bold=True)
    p.add_run("\t")
    vr = p.add_run(value or none)
    _set_run_font(vr)


def _add_stacked_field(doc: Document, label: str, value: str) -> None:
    p = doc.add_paragraph()
    _para_tab(p, before=8)
    lr = p.add_run(f"{label}:")
    _set_run_font(lr, bold=True)

    if value:
        p2 = doc.add_paragraph()
        _para_tab(p2)
        vr = p2.add_run(value)
        _set_run_font(vr)


def _add_split_label_field(doc: Document, line1: str, line2: str, value: str) -> None:
    p1 = doc.add_paragraph()
    _para_tab(p1, before=8)
    r1 = p1.add_run(line1)
    _set_run_font(r1, bold=True)

    p2 = doc.add_paragraph()
    _para_tab(p2)
    r2 = p2.add_run(f"{line2}:")
    _set_run_font(r2, bold=True)

    if value:
        p3 = doc.add_paragraph()
        _para_tab(p3)
        vr = p3.add_run(value)
        _set_run_font(vr)


def generate_obyektivka_docx(
    user_data: dict[str, Any] | None = None,
    photo_path: str | None = None,
    output_filepath: str | None = None,
    **kwargs: Any,
) -> str:
    data = user_data or kwargs.get("data") or {}
    temp_photo_from_data = None
    if not photo_path or not os.path.exists(photo_path):
        photo_data = _to_text(data.get("photo_data"))
        try:
            if photo_data.startswith("data:image/") and "," in photo_data:
                photo_data = process_passport_photo(photo_data)
                header, b64 = photo_data.split(",", 1)
                mime = header.split(";")[0].split(":")[1].lower()
                ext = {
                    "image/png": "png",
                    "image/jpeg": "jpg",
                    "image/jpg": "jpg",
                    "image/webp": "webp",
                }.get(mime, "jpg")
                os.makedirs("temp", exist_ok=True)
                temp_photo_from_data = os.path.join("temp", f"oby_local_photo_{os.getpid()}.{ext}")
                with open(temp_photo_from_data, "wb") as f:
                    f.write(base64.b64decode(b64))
                photo_path = temp_photo_from_data
        except Exception as exc:
            logger.warning("Failed to decode photo_data in generator: %s", exc)
            photo_path = None

    if not isinstance(data, dict):
        raise ValueError("user_data must be a dictionary")

    if not output_filepath:
        os.makedirs("temp", exist_ok=True)
        safe_name = (_to_text(data.get("fullname")) or "Obyektivka").replace(" ", "_").replace("/", "_")
        output_filepath = os.path.join("temp", f"obyektivka_{safe_name}_@DastyorAiBot.docx")
    else:
        os.makedirs(os.path.dirname(output_filepath) or ".", exist_ok=True)

    lang = _to_text(data.get("lang")) or "uz_lat"
    L = labels_for(lang)
    none = L["none"]

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(FONT_BODY_PT)
    style.paragraph_format.line_spacing = LINE_HEIGHT
    style.paragraph_format.space_after = Pt(0)
    for section in doc.sections:
        section.top_margin = Cm(PAGE_MARGIN_TOP_MM / 10)
        section.bottom_margin = Cm(PAGE_MARGIN_BOTTOM_MM / 10)
        section.left_margin = Cm(PAGE_MARGIN_LEFT_MM / 10)
        section.right_margin = Cm(PAGE_MARGIN_RIGHT_MM / 10)

    full_name = _to_text(data.get("fullname")) or "FAMILIYA ISM SHARIF"
    work_items = _parse_list(data.get("work_experience"))

    current_job = _to_text(data.get("current_job"))
    current_job_year = _to_text(data.get("current_job_year"))
    if not current_job:
        for idx, item in enumerate(work_items):
            year_raw = _to_text(item.get("year") or item.get("from"))
            year_norm = re.sub(r"[\s.\-_/]", "", year_raw.lower())
            is_current = any(
                key in year_norm
                for key in ("hv", "hvgacha", "hozirgacha", "ҳв", "ҳвгача", "ҳозиргача")
            )
            position_raw = _to_text(item.get("position") or item.get("description") or item.get("job"))
            if is_current and position_raw:
                current_job = position_raw
                if not current_job_year:
                    from_raw = _to_text(item.get("from"))
                    if from_raw:
                        current_job_year = from_raw
                    else:
                        match = re.search(r"(19|20)\d{2}", year_raw)
                        if match:
                            current_job_year = match.group(0)
                work_items.pop(idx)
                break

    section = doc.sections[0]
    total_width = section.page_width - section.left_margin - section.right_margin
    photo_col_width = Cm(PHOTO_WIDTH_MM / 10 + 0.2)
    text_col_width = int(total_width - photo_col_width)

    hdr_tbl = doc.add_table(rows=1, cols=2)
    hdr_tbl.autofit = False
    hdr_tbl.columns[0].width = text_col_width
    hdr_tbl.columns[1].width = photo_col_width
    _set_table_no_borders_strict(hdr_tbl)
    left_hdr = hdr_tbl.cell(0, 0)
    right_hdr = hdr_tbl.cell(0, 1)
    left_hdr.vertical_alignment = WD_ALIGN_VERTICAL.TOP
    right_hdr.vertical_alignment = WD_ALIGN_VERTICAL.TOP

    t_p = left_hdr.paragraphs[0]
    t_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tr = t_p.add_run(L["title"])
    _set_run_font(tr, size=FONT_TITLE_PT, bold=True)
    t_p.paragraph_format.space_after = Pt(4)

    n_p = left_hdr.add_paragraph()
    n_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    nr = n_p.add_run(full_name)
    _set_run_font(nr, size=FONT_TITLE_PT, bold=True)
    n_p.paragraph_format.space_after = Pt(4)

    photo_p = right_hdr.paragraphs[0]
    photo_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if photo_path and os.path.exists(photo_path):
        try:
            run = photo_p.add_run()
            run.add_picture(photo_path, width=Cm(PHOTO_WIDTH_MM / 10), height=Cm(PHOTO_HEIGHT_MM / 10))
        except Exception as exc:
            logger.warning("Failed to insert photo: %s", exc)
            ph = photo_p.add_run(L["photo_hint"])
            _set_run_font(ph, size=7)
    else:
        ph = photo_p.add_run(L["photo_hint"])
        _set_run_font(ph, size=7)

    if current_job:
        if current_job_year:
            yr_p = doc.add_paragraph()
            _para_tab(yr_p)
            yr_run = yr_p.add_run(f"{current_job_year.rstrip('.')}:")
            _set_run_font(yr_run)
        job_p = doc.add_paragraph()
        _para_tab(job_p, after=4)
        pos_run = job_p.add_run(current_job)
        _set_run_font(pos_run)

    _add_two_col_pair(
        doc,
        L["r1l"],
        _to_text(data.get("birthdate")),
        L["r1r"],
        _to_text(data.get("birthplace")),
        none=none,
    )
    _add_two_col_pair(
        doc,
        L["r2l"],
        _to_text(data.get("nation")),
        L["r2r"],
        _to_text(data.get("party")),
        none=none,
    )
    _add_two_col_pair(
        doc,
        L["r3l"],
        _to_text(data.get("education")),
        L["r3r"],
        _to_text(data.get("graduated")),
        none=none,
    )
    _add_inline_field(doc, L["rSpec"], _to_text(data.get("specialty")), none=none)
    _add_two_col_pair(
        doc,
        L["r4l"],
        _to_text(data.get("degree")),
        L["r4r"],
        _to_text(data.get("scientific_title")),
        none=none,
    )
    _add_two_col_pair(
        doc,
        L["r5l"],
        _to_text(data.get("languages")),
        L["r5r"],
        _to_text(data.get("military_rank")),
        none=none,
    )
    _add_stacked_field(doc, L["rAw"], _to_text(data.get("awards")))
    _add_stacked_field(doc, L["rIdo"], _to_text(data.get("departmental_awards")))
    _add_split_label_field(doc, L["rDep1"], L["rDep2"], _to_text(data.get("deputy")))

    work_title = doc.add_paragraph()
    work_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    wr = work_title.add_run(L["work"])
    _set_run_font(wr, size=FONT_TITLE_PT, bold=True)
    work_title.paragraph_format.space_before = Pt(0)
    work_title.paragraph_format.space_after = Pt(4)

    yy_suffix = "йй." if lang == "uz_cyr" else "yy."
    if work_items:
        for item in work_items:
            year = _to_text(item.get("year")) or _to_text(item.get("from"))
            end = _to_text(item.get("to"))
            if year and end and yy_suffix.rstrip(".") not in year.lower():
                year = f"{year}-{end} {yy_suffix}"
            year = year.rstrip(".") if year else year
            position = _to_text(item.get("position") or item.get("description") or item.get("job"))
            if not (year or position):
                continue
            p = doc.add_paragraph()
            _para_tab(p, before=4)
            if year and position:
                yshow = year if (yy_suffix.rstrip(".") in year.lower()) else f"{year} {yy_suffix}"
                line = f"{yshow} - {position}"
            else:
                line = year or position
            wrun = p.add_run(line)
            _set_run_font(wrun)
    else:
        p = doc.add_paragraph("-")
        _set_run_font(p.runs[0] if p.runs else p.add_run("-"))

    relatives = _parse_list(data.get("relatives"))
    doc.add_page_break()

    t1 = doc.add_paragraph()
    t1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = t1.add_run(f"{full_name}{L['rel_line1_suffix']}")
    _set_run_font(r1, size=FONT_REL_TITLE_PT, bold=True)
    t1.paragraph_format.space_after = Pt(0)

    t2 = doc.add_paragraph()
    t2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = t2.add_run(L["rel_line2"])
    _set_run_font(r2, size=FONT_REL_TITLE_PT, bold=True)
    t2.paragraph_format.space_after = Pt(6)

    rel_tbl = doc.add_table(rows=1, cols=5)
    rel_tbl.autofit = False
    _set_col_widths_dxa(rel_tbl, REL_COL_DXA)
    _set_table_borders(rel_tbl, size_pt=1.0)

    headers = [L["qar"], L["fish"], L["tug"], L["ish"], L["tur"]]
    for i, h in enumerate(headers):
        cell = rel_tbl.rows[0].cells[i]
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(h.replace(" ", "\n", 1) if i in (1, 2, 3) and "\n" not in h else h)
        _set_run_font(run, bold=True)
        run.underline = True

    if relatives:
        for rel in relatives:
            row = rel_tbl.add_row().cells
            vals = [
                _to_text(rel.get("degree") or rel.get("type")),
                _to_text(rel.get("fullname") or rel.get("name")),
                _to_text(rel.get("birth_year_place") or rel.get("birth")),
                _to_text(rel.get("work_place") or rel.get("job")),
                _to_text(rel.get("address") or rel.get("addr")),
            ]
            for i, val in enumerate(vals):
                cell = row[i]
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                rr = p.add_run(val or none)
                _set_run_font(rr, bold=(i == 0))
    else:
        row = rel_tbl.add_row().cells
        merged = row[0].merge(row[4])
        p = merged.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(L["no_rel"])
        _set_run_font(run)

    doc.save(output_filepath)
    if temp_photo_from_data and os.path.exists(temp_photo_from_data):
        try:
            os.remove(temp_photo_from_data)
        except Exception:
            pass
    return output_filepath
