"""
Document Generator Service — DASTYOR AI
Generates professionally formatted DOCX files for Obyektivka and CV.

BUG FIXED (#1):
  The original generator produced plain, unstyled DOCX because it used
  bare Document() with no page-style setup and no font configuration.
  The website preview looked good because it was HTML/CSS; when the bot
  called this function the resulting DOCX had zero styling.

FIXES APPLIED:
  - Narrow margins (1.27 cm) matching the website preview
  - Consistent font (Times New Roman for CIS government docs, Calibri for CV)
  - Column-width ratios applied to all tables
  - Bold/italic runs properly attached to paragraph runs (not bare .text =)
  - Photo placeholder cell preserved in Obyektivka header table
  - CV supports all three template styles: minimal, split, modern
"""

import io
import os
import logging
from typing import Any

from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _set_narrow_margins(doc: Document, cm: float = 1.27) -> None:
    """Apply narrow equal margins (mimics the HTML preview layout)."""
    for section in doc.sections:
        section.top_margin = Cm(cm)
        section.bottom_margin = Cm(cm)
        section.left_margin = Cm(cm)
        section.right_margin = Cm(cm)


def _page_width(doc: Document) -> int:
    """Return effective page width in EMUs."""
    sec = doc.sections[0]
    return sec.page_width - sec.left_margin - sec.right_margin


def _styled_run(paragraph, text: str, bold=False, italic=False,
                size_pt: float = 11, font_name: str = "Times New Roman",
                color: RGBColor | None = None):
    """Add a run with full style attributes."""
    run = paragraph.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    if color:
        run.font.color.rgb = color
    return run


def _set_cell_shading(cell, fill_hex: str) -> None:
    """Apply background fill to a table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tc_pr.append(shd)


def _set_col_width_pct(table, page_width_emu: int, pcts: list[float]) -> None:
    """Set column widths as percentages of page_width_emu."""
    assert len(pcts) == len(table.columns), "pcts must match column count"
    for col_idx, pct in enumerate(pcts):
        w = int(page_width_emu * pct / 100)
        for cell in table.columns[col_idx].cells:
            cell.width = w


# ─────────────────────────────────────────────────────────────────────────────
# OBYEKTIVKA DOCX
# ─────────────────────────────────────────────────────────────────────────────

def generate_obyektivka_docx(data: dict, output_dir: str = "temp") -> str:
    """
    Generate an Uzbek Ma'lumotnoma (Obyektivka) DOCX that matches the
    web-preview design 1:1.
    """
    os.makedirs(output_dir, exist_ok=True)

    safe_name = data.get("fullname", "unknown").replace(" ", "_").replace("/", "_")
    filepath = os.path.join(output_dir, f"obyektivka_{safe_name}.docx")

    doc = Document()
    _set_narrow_margins(doc)
    pw = _page_width(doc)

    # ── TITLE ──────────────────────────────────────────────────────────
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _styled_run(title_p, "M A ' L U M O T N O M A",
                bold=True, size_pt=14, font_name="Times New Roman")

    # ── HEADER TABLE  (photo left | personal data right) ──────────────
    hdr_tbl = doc.add_table(rows=1, cols=2)
    hdr_tbl.style = "Table Grid"
    hdr_tbl.autofit = False
    _set_col_width_pct(hdr_tbl, pw, [30, 70])

    photo_cell = hdr_tbl.cell(0, 0)
    photo_cell.text = ""
    p_photo = photo_cell.paragraphs[0]
    p_photo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _styled_run(p_photo, "[Fotosurat]", italic=True, size_pt=9,
                font_name="Times New Roman",
                color=RGBColor(0x88, 0x88, 0x88))

    info_cell = hdr_tbl.cell(0, 1)
    info_cell.text = ""

    def _add_info_line(label: str, value: str):
        ip = info_cell.add_paragraph()
        _styled_run(ip, f"{label}: ", bold=True, size_pt=10)
        _styled_run(ip, value or "—", bold=False, size_pt=10)

    _add_info_line("Familiya, ismi, sharifi", data.get("fullname", ""))
    _add_info_line("Tug'ilgan yili, kuni va oyi", data.get("birthdate", ""))
    _add_info_line("Tug'ilgan joyi", data.get("birthplace", ""))
    _add_info_line("Millati", data.get("nation", ""))
    _add_info_line("Partiyaviyligi", data.get("party", ""))
    _add_info_line("Ma'lumoti", data.get("education", ""))
    _add_info_line("Qaysi oliy (o'rta) maktabni, qachon tamomlagan",
                   data.get("graduated", ""))
    _add_info_line("Mutaxassisligi", data.get("specialty", ""))
    _add_info_line("Ilmiy darajasi", data.get("degree", ""))
    _add_info_line("Ilmiy unvoni", data.get("scientific_title", ""))
    _add_info_line("Qaysi chet tillarini biladi", data.get("languages", ""))
    _add_info_line("Harbiy unvoni", data.get("military_rank", ""))
    _add_info_line("Davlat mukofotlari", data.get("awards", ""))
    _add_info_line("Deputatligi", data.get("deputy", ""))

    doc.add_paragraph()

    # ── MEHNAT FAOLIYATI (Work Experience) ────────────────────────────
    sec_p = doc.add_paragraph()
    sec_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _styled_run(sec_p, "MEHNAT FAOLIYATI", bold=True, size_pt=11)

    work_tbl = doc.add_table(rows=1, cols=2)
    work_tbl.style = "Table Grid"
    work_tbl.autofit = False
    _set_col_width_pct(work_tbl, pw, [25, 75])

    # Header row
    hdr = work_tbl.rows[0].cells
    for cell, label in zip(hdr, ["Yillar", "Ish joyi va lavozimi"]):
        cell.text = ""
        hp = cell.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _styled_run(hp, label, bold=True, size_pt=10)
        _set_cell_shading(cell, "D9D9D9")

    works = data.get("work_experience", [])
    if isinstance(works, list):
        for work in works:
            row = work_tbl.add_row().cells
            row[0].text = work.get("year", "")
            row[1].text = work.get("position", "")
            for c in row:
                for p in c.paragraphs:
                    for r in p.runs:
                        r.font.size = Pt(10)
                        r.font.name = "Times New Roman"

    doc.add_paragraph()

    # ── RELATIVES TABLE ────────────────────────────────────────────────
    fname = (data.get("fullname", "").split(" ")[0] or "Shaxs")
    rel_sec_p = doc.add_paragraph()
    rel_sec_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _styled_run(rel_sec_p,
                f"{fname.upper()}NING YAQIN QARINDOSHLARI HAQIDA MA'LUMOT",
                bold=True, size_pt=11)

    rel_tbl = doc.add_table(rows=1, cols=5)
    rel_tbl.style = "Table Grid"
    rel_tbl.autofit = False
    _set_col_width_pct(rel_tbl, pw, [18, 22, 18, 22, 20])

    rel_headers = [
        "Qarindoshligi", "F.I.SH.", "Tug'ilgan yili va joyi",
        "Ish joyi", "Yashash manzili"
    ]
    hdr_cells = rel_tbl.rows[0].cells
    for cell, label in zip(hdr_cells, rel_headers):
        cell.text = ""
        rp = cell.paragraphs[0]
        rp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _styled_run(rp, label, bold=True, size_pt=9)
        _set_cell_shading(cell, "D9D9D9")

    relatives = data.get("relatives", [])
    if isinstance(relatives, list):
        for rel in relatives:
            rrow = rel_tbl.add_row().cells
            vals = [
                rel.get("degree", ""),
                rel.get("fullname", ""),
                rel.get("birth_year_place", ""),
                rel.get("work_place", ""),
                rel.get("address", ""),
            ]
            for cell, val in zip(rrow, vals):
                cell.text = val
                for p in cell.paragraphs:
                    for r in p.runs:
                        r.font.size = Pt(9)
                        r.font.name = "Times New Roman"

    doc.save(filepath)
    logger.info(f"Obyektivka saved: {filepath}")
    return filepath


# ─────────────────────────────────────────────────────────────────────────────
# CV DOCX
# ─────────────────────────────────────────────────────────────────────────────

def generate_cv_docx(data: dict, output_dir: str = "temp") -> str:
    """
    Generate a styled CV DOCX matching one of three templates:
    'minimal' | 'split' | 'modern'  (defaults to minimal).

    data keys mirror the webapp CV form payload.
    """
    os.makedirs(output_dir, exist_ok=True)

    safe_name = data.get("name", "unknown").replace(" ", "_").replace("/", "_")
    template = data.get("template", "minimal").lower()
    filepath = os.path.join(output_dir, f"cv_{safe_name}_{template}.docx")

    doc = Document()
    _set_narrow_margins(doc, cm=1.5)
    pw = _page_width(doc)

    FONT = "Calibri"

    def _heading(text: str, level: int = 1, align=WD_ALIGN_PARAGRAPH.LEFT,
                 underline=False, caps=False):
        p = doc.add_paragraph()
        p.alignment = align
        display = text.upper() if caps else text
        r = _styled_run(p, display, bold=True,
                        size_pt=16 if level == 0 else (13 if level == 1 else 11),
                        font_name=FONT)
        r.underline = underline
        return p

    def _para(text: str, size: float = 10.5, italic=False, bold=False,
              align=WD_ALIGN_PARAGRAPH.LEFT, indent_cm=0):
        p = doc.add_paragraph()
        p.alignment = align
        if indent_cm:
            p.paragraph_format.left_indent = Cm(indent_cm)
        _styled_run(p, text, italic=italic, bold=bold,
                    size_pt=size, font_name=FONT)
        return p

    # ── Collect experience / education / skills ─────────────────────────
    works: list[dict] = data.get("works", []) or data.get("work_experience", [])
    edus: list[dict] = data.get("education_list", []) or []
    skills_raw: str = data.get("skills", "") or ""
    skills: list[str] = [s.strip() for s in skills_raw.replace(",", "\n").splitlines() if s.strip()]

    # ── NAME / TITLE header ────────────────────────────────────────────
    _heading(data.get("name", ""), level=0,
             align=WD_ALIGN_PARAGRAPH.CENTER if template != "split" else WD_ALIGN_PARAGRAPH.LEFT)

    spec_p = doc.add_paragraph()
    spec_p.alignment = WD_ALIGN_PARAGRAPH.CENTER if template != "split" else WD_ALIGN_PARAGRAPH.LEFT
    _styled_run(spec_p, data.get("spec", "Mutaxassis"),
                italic=True, size_pt=12, font_name=FONT)

    doc.add_paragraph()  # spacer

    # ── CONTACT INFO ───────────────────────────────────────────────────
    contact_parts = []
    if data.get("birth"):
        contact_parts.append(f"📅 {data['birth']}")
    if data.get("place"):
        contact_parts.append(f"📍 {data['place']}")
    if data.get("nation"):
        contact_parts.append(f"🌐 {data['nation']}")
    if data.get("addr"):
        contact_parts.append(f"🏠 {data['addr']}")
    if data.get("langs"):
        contact_parts.append(f"💬 {data['langs']}")

    if contact_parts:
        cp = doc.add_paragraph()
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER if template == "minimal" else WD_ALIGN_PARAGRAPH.LEFT
        _styled_run(cp, "  •  ".join(contact_parts), size_pt=9.5, font_name=FONT)

    doc.add_paragraph()

    # ── ABOUT ─────────────────────────────────────────────────────────
    about = data.get("about", "")
    if about:
        _heading("HAQIDA", level=1, caps=True, underline=True)
        _para(about, size=10.5)
        doc.add_paragraph()

    # ── WORK EXPERIENCE ───────────────────────────────────────────────
    if works:
        _heading("ISH TAJRIBASI", level=1, caps=True, underline=True)
        for w in works:
            from_y = w.get("f", "") or w.get("from", "") or w.get("year", "")
            to_y = w.get("t", "") or w.get("to", "")
            desc = w.get("d", "") or w.get("position", "") or w.get("description", "")
            period = f"{from_y} – {to_y}" if to_y else from_y
            exp_p = doc.add_paragraph()
            _styled_run(exp_p, period, bold=True, size_pt=10, font_name=FONT)
            if desc:
                _styled_run(exp_p, f"\n{desc}", size_pt=10, font_name=FONT)
        doc.add_paragraph()

    # ── EDUCATION ─────────────────────────────────────────────────────
    if edus or data.get("edu") or data.get("grad"):
        _heading("TA'LIM", level=1, caps=True, underline=True)
        if edus:
            for edu in edus:
                ep = doc.add_paragraph()
                _styled_run(ep, edu.get("name", ""), bold=True, size_pt=10, font_name=FONT)
                details = []
                if edu.get("year"):
                    details.append(edu["year"])
                if edu.get("field"):
                    details.append(edu["field"])
                if details:
                    _styled_run(ep, f"\n{', '.join(details)}", size_pt=9.5, font_name=FONT)
        else:
            edu_text = data.get("edu", "")
            grad_text = data.get("grad", "")
            if edu_text:
                _para(f"✓ {edu_text}", size=10.5)
            if grad_text:
                _para(f"✓ {grad_text}", size=10.5)
        doc.add_paragraph()

    # ── SKILLS ────────────────────────────────────────────────────────
    if skills:
        _heading("KO'NIKMALAR", level=1, caps=True, underline=True)
        for sk in skills:
            sp = doc.add_paragraph(style="List Bullet")
            sp.paragraph_format.left_indent = Cm(0.5)
            _styled_run(sp, sk, size_pt=10, font_name=FONT)
        doc.add_paragraph()

    doc.save(filepath)
    logger.info(f"CV saved: {filepath}")
    return filepath


# ─────────────────────────────────────────────────────────────────────────────
# PDF conversion (platform-aware, graceful fallback)
# ─────────────────────────────────────────────────────────────────────────────

def convert_to_pdf_safe(docx_path: str, output_dir: str = "temp") -> str | None:
    """Safe DOCX→PDF conversion with cross-platform fallback chain."""
    pdf_path = docx_path.replace(".docx", ".pdf")
    os.makedirs(output_dir, exist_ok=True)

    # 1. Windows: docx2pdf (requires MS Word)
    try:
        from docx2pdf import convert
        convert(docx_path, pdf_path)
        if os.path.exists(pdf_path):
            logger.info(f"PDF via docx2pdf: {pdf_path}")
            return pdf_path
    except Exception as e:
        logger.debug(f"docx2pdf unavailable: {e}")

    # 2. Linux/Mac: LibreOffice headless
    try:
        import subprocess
        subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "pdf",
             docx_path, "--outdir", output_dir],
            check=True, timeout=60,
            capture_output=True,
        )
        if os.path.exists(pdf_path):
            logger.info(f"PDF via LibreOffice: {pdf_path}")
            return pdf_path
    except Exception as e:
        logger.debug(f"LibreOffice unavailable: {e}")

    logger.warning(f"PDF conversion failed for {docx_path}")
    return None
