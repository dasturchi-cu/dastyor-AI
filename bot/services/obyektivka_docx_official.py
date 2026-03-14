"""
Official Obyektivka (Ma'lumotnoma) DOCX generator.
"""

import json
import logging
import os
from typing import Any

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
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


def _add_label_value(paragraph, label: str, value: str) -> None:
    run_label = paragraph.add_run(f"{label}: ")
    run_label.bold = True
    paragraph.add_run(value or "yo'q")
    paragraph.paragraph_format.space_after = Pt(3)
    paragraph.paragraph_format.line_spacing = 1.12


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

    # Right-aligned photo block (no table in main section).
    pp = doc.add_paragraph()
    pp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    pp.paragraph_format.right_indent = Cm(0.2)
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
        ("Davlat mukofotlari bilan taqdirlanganmi (qanaqa)", _to_text(data.get("awards"))),
        ("Xalq deputatlari respublika, viloyat, shahar va tuman Kengashi deputatimi yoki boshqa saylanadigan organlar a'zosimi (to'liq ko'rsatilishi lozim)", _to_text(data.get("deputy"))),
    ]
    for label, value in rows:
        p = doc.add_paragraph()
        _add_label_value(p, label, value)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)
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

    # Second page: relatives table (visible grid, official style).
    relatives = _parse_list(data.get("relatives"))
    doc.add_page_break()
    rel_title = doc.add_paragraph()
    rel_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rel_title_run = rel_title.add_run(f"{full_name}ning yaqin qarindoshlari haqida")
    rel_title_run.bold = True
    rel_title_run.font.size = Pt(12)

    rel_sub = doc.add_paragraph()
    rel_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rel_sub_run = rel_sub.add_run("MA'LUMOTNOMA")
    rel_sub_run.bold = True
    rel_sub_run.font.size = Pt(12)

    rel_tbl = doc.add_table(rows=1, cols=5)
    rel_tbl.style = "Table Grid"
    rel_tbl.autofit = False
    rel_tbl.columns[0].width = Cm(2.8)
    rel_tbl.columns[1].width = Cm(4.0)
    rel_tbl.columns[2].width = Cm(3.2)
    rel_tbl.columns[3].width = Cm(3.2)
    rel_tbl.columns[4].width = Cm(3.2)

    headers = [
        "Qarindoshligi",
        "Familiyasi ismi va\notasining ismi",
        "Tug'ilgan yili\nva joyi",
        "Ish joyi va\nlavozimi",
        "Turar joyi",
    ]
    for i, h in enumerate(headers):
        hp = rel_tbl.rows[0].cells[i].paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        hr = hp.add_run(h)
        hr.bold = True
        hr.font.size = Pt(10)

    if relatives:
        for r in relatives:
            row = rel_tbl.add_row().cells
            rel_type = _to_text(r.get("degree") or r.get("type"))
            rel_name = _to_text(r.get("fullname") or r.get("name"))
            rel_birth = _to_text(r.get("birth_year_place") or r.get("birth"))
            rel_work = _to_text(r.get("work_place") or r.get("job"))
            rel_addr = _to_text(r.get("address") or r.get("addr"))
            vals = [rel_type, rel_name, rel_birth, rel_work, rel_addr]
            for i, val in enumerate(vals):
                p = row[i].paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.add_run(val or "yo'q")
                run.font.size = Pt(10)
                if i == 0:
                    run.bold = True
    else:
        row = rel_tbl.add_row().cells
        merged = row[0].merge(row[4])
        p = merged.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run("Yaqin qarindoshlar haqida ma'lumot kiritilmagan.")

    doc.save(output_filepath)
    return output_filepath
