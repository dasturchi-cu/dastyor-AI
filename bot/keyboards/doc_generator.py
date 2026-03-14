"""
CV DOCX generator.
"""

import os
from typing import Any

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _parse_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return value
    return []


def generate_cv_docx(data: dict[str, Any], output_dir: str = "temp") -> str:
    os.makedirs(output_dir, exist_ok=True)
    safe_name = (_as_text(data.get("name")) or "CV").replace(" ", "_").replace("/", "_")
    filepath = os.path.join(output_dir, f"cv_{safe_name}_@DastyorAiBot.docx")

    doc = Document()
    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2)
        section.right_margin = Cm(2)

    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(11)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = title.add_run(_as_text(data.get("name")) or "CV")
    r.bold = True
    r.font.size = Pt(18)

    spec = _as_text(data.get("spec"))
    if spec:
        sub = doc.add_paragraph()
        sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sr = sub.add_run(spec)
        sr.italic = True
        sr.font.size = Pt(12)

    contacts = []
    for key in ("phone", "email", "loc"):
        val = _as_text(data.get(key))
        if val:
            contacts.append(val)
    if contacts:
        p = doc.add_paragraph(" | ".join(contacts))
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(12)

    about = _as_text(data.get("about"))
    if about:
        h = doc.add_paragraph("HAQIDA")
        h.runs[0].bold = True
        doc.add_paragraph(about)

    works = _parse_list(data.get("works") or data.get("work_experience"))
    if works:
        h = doc.add_paragraph("ISH TAJRIBASI")
        h.runs[0].bold = True
        for item in works:
            year = _as_text(item.get("year") or item.get("from"))
            to = _as_text(item.get("to"))
            if year and to:
                period = f"{year}-{to}"
            else:
                period = year or to
            role = _as_text(item.get("position") or item.get("description") or item.get("title"))
            line = f"{period} - {role}" if period and role else (period or role)
            if line:
                doc.add_paragraph(line)

    education = _parse_list(data.get("education_list"))
    if education:
        h = doc.add_paragraph("TA'LIM")
        h.runs[0].bold = True
        for item in education:
            title_text = _as_text(item.get("title") or item.get("name"))
            date_text = _as_text(item.get("date") or item.get("year"))
            line = f"{date_text} - {title_text}" if date_text and title_text else (date_text or title_text)
            if line:
                doc.add_paragraph(line)

    skills = _as_text(data.get("skills"))
    if skills:
        h = doc.add_paragraph("KO'NIKMALAR")
        h.runs[0].bold = True
        for part in [s.strip() for s in skills.replace(",", "\n").splitlines() if s.strip()]:
            doc.add_paragraph(f"- {part}")

    doc.save(filepath)
    return filepath
