"""
Official Obyektivka (Ma'lumotnoma) DOCX generator.
"""

import json
import logging
import os
from typing import Any

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

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


def _remove_table_borders(table) -> None:
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), "nil")
        borders.append(el)
    tbl_pr.append(borders)


def generate_obyektivka_docx(
    user_data: dict[str, Any] | None = None,
    photo_path: str | None = None,
    output_filepath: str | None = None,
    **kwargs: Any,
) -> str:
    data = user_data or kwargs.get("data") or {}
    if not isinstance(data, dict):
        raise ValueError("user_data must be a dictionary")

    if not output_filepath:
        os.makedirs("temp", exist_ok=True)
        safe_name = (_to_text(data.get("fullname")) or "Obyektivka").replace(" ", "_").replace("/", "_")
        output_filepath = os.path.join("temp", f"obyektivka_{safe_name}_@DastyorAiBot.docx")
    else:
        os.makedirs(os.path.dirname(output_filepath) or ".", exist_ok=True)

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)
    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rt = title.add_run("MA'LUMOTNOMA")
    rt.bold = True
    rt.font.size = Pt(15)
    title.paragraph_format.space_after = Pt(8)

    full_name = _to_text(data.get("fullname")) or "FAMILIYA ISM SHARIF"
    name = doc.add_paragraph()
    name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rn = name.add_run(full_name)
    rn.bold = True
    rn.font.size = Pt(13)
    name.paragraph_format.space_after = Pt(10)

    layout = doc.add_table(rows=1, cols=2)
    layout.autofit = False
    _remove_table_borders(layout)
    layout.columns[0].width = Cm(12.5)
    layout.columns[1].width = Cm(3.8)

    left_cell = layout.cell(0, 0)
    right_cell = layout.cell(0, 1)
    left_cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP
    right_cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP

    rows = [
        ("Tug'ilgan yili", _to_text(data.get("birthdate"))),
        ("Tug'ilgan joyi", _to_text(data.get("birthplace"))),
        ("Millati", _to_text(data.get("nation"))),
        ("Partiyaviyligi", _to_text(data.get("party"))),
        ("Ma'lumoti", _to_text(data.get("education"))),
        ("Tamomlagan", _to_text(data.get("graduated"))),
        ("Ma'lumoti bo'yicha mutaxassisligi", _to_text(data.get("specialty"))),
        ("Ilmiy darajasi", _to_text(data.get("degree"))),
        ("Ilmiy unvoni", _to_text(data.get("scientific_title"))),
        ("Qaysi chet tillarini biladi", _to_text(data.get("languages"))),
        ("Harbiy unvoni", _to_text(data.get("military_rank"))),
        ("Davlat mukofotlari bilan taqdirlanganmi", _to_text(data.get("awards"))),
        ("Deputatlik yoki saylangan lavozimlar", _to_text(data.get("deputy"))),
    ]
    for idx, (label, value) in enumerate(rows):
        p = left_cell.paragraphs[0] if idx == 0 else left_cell.add_paragraph()
        rb = p.add_run(f"{label}: ")
        rb.bold = True
        p.add_run(value or "-")
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15

    pp = right_cell.paragraphs[0]
    pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if photo_path and os.path.exists(photo_path):
        try:
            rr = pp.add_run()
            rr.add_picture(photo_path, width=Cm(3), height=Cm(4))
        except Exception as exc:
            logger.warning("Failed to insert photo: %s", exc)
            hold = pp.add_run("[3x4 foto]")
            hold.italic = True
    else:
        hold = pp.add_run("[3x4 foto]")
        hold.italic = True

    doc.add_paragraph().paragraph_format.space_after = Pt(6)
    sec = doc.add_paragraph()
    sec.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rs = sec.add_run("MEHNAT FAOLIYATI")
    rs.bold = True
    rs.font.size = Pt(12)
    sec.paragraph_format.space_after = Pt(6)

    work_items = _parse_list(data.get("work_experience"))
    current_job = _to_text(data.get("current_job"))
    current_job_year = _to_text(data.get("current_job_year"))
    if current_job:
        work_items = [{"year": current_job_year or "Hozirgi", "position": current_job}] + work_items

    if work_items:
        for item in work_items:
            year = _to_text(item.get("year")) or _to_text(item.get("from"))
            end = _to_text(item.get("to"))
            if year and end:
                year = f"{year}-{end} yy."
            position = _to_text(item.get("position") or item.get("description") or item.get("job"))
            if not (year or position):
                continue
            ln = doc.add_paragraph(f"{year} – {position}" if year and position else (year or position))
            ln.paragraph_format.space_after = Pt(3)
            ln.paragraph_format.line_spacing = 1.15
    else:
        doc.add_paragraph("-")

    doc.save(output_filepath)
    return output_filepath
