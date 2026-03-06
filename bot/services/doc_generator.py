"""
Document Generator Service — DASTYOR AI
Generates professionally formatted DOCX files for Obyektivka and CV.
Supports 4 languages: uz_lat | uz_cyr | en | ru
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
    for section in doc.sections:
        section.top_margin = Cm(cm)
        section.bottom_margin = Cm(cm)
        section.left_margin = Cm(cm)
        section.right_margin = Cm(cm)


def _page_width(doc: Document) -> int:
    sec = doc.sections[0]
    return sec.page_width - sec.left_margin - sec.right_margin


def _styled_run(paragraph, text: str, bold=False, italic=False,
                size_pt: float = 11, font_name: str = "Times New Roman",
                color: RGBColor | None = None):
    run = paragraph.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    if color:
        run.font.color.rgb = color
    return run


def _set_cell_shading(cell, fill_hex: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tc_pr.append(shd)


def _set_col_width_pct(table, page_width_emu: int, pcts: list) -> None:
    assert len(pcts) == len(table.columns), "pcts must match column count"
    for col_idx, pct in enumerate(pcts):
        w = int(page_width_emu * pct / 100)
        for cell in table.columns[col_idx].cells:
            cell.width = w


# ─────────────────────────────────────────────────────────────────────────────
# Multilingual labels for Obyektivka DOCX
# ─────────────────────────────────────────────────────────────────────────────

_OBY_LABELS = {
    "uz_lat": {
        "title":      "M A ' L U M O T N O M A",
        "fullname":   "Familiya, ismi, sharifi",
        "bdate":      "Tug'ilgan yili, kuni va oyi",
        "bplace":     "Tug'ilgan joyi",
        "nation":     "Millati",
        "party":      "Partiyaviyligi",
        "edu":        "Ma'lumoti",
        "grad":       "Qaysi oliy (o'rta) maktabni, qachon tamomlagan",
        "spec":       "Mutaxassisligi",
        "degree":     "Ilmiy darajasi",
        "stitle":     "Ilmiy unvoni",
        "langs":      "Qaysi chet tillarini biladi",
        "military":   "Harbiy unvoni",
        "awards":     "Davlat mukofotlari",
        "deputy":     "Deputatmi yoki boshqa saylanadigan organlar a'zosimi",
        "work_title": "MEHNAT FAOLIYATI",
        "yillar":     "Yillar",
        "lavozim":    "Ish joyi va lavozimi",
        "rel_title":  "NING YAQIN QARINDOSHLARI HAQIDA MA'LUMOT",
        "rel_kin":    "Qarindoshligi",
        "rel_fish":   "F.I.SH.",
        "rel_birth":  "Tug'ilgan yili va joyi",
        "rel_work":   "Ish joyi va lavozimi",
        "rel_addr":   "Yashash manzili",
        "photo":      "[Fotosurat]",
        "ru_prefix":  "",
    },
    "uz_cyr": {
        "title":      "\u041c \u0410 \u042a \u041b \u0423 \u041c \u041e \u0422 \u041d \u041e \u041c \u0410",
        "fullname":   "\u0424\u0430\u043c\u0438\u043b\u0438\u044f, \u0438\u0441\u043c\u0438, \u0448\u0430\u0440\u0438\u0444\u0438",
        "bdate":      "\u0422\u0443\u0493\u0438\u043b\u0433\u0430\u043d \u0439\u0438\u043b\u0438, \u043a\u0443\u043d\u0438 \u0432\u0430 \u043e\u0439\u0438",
        "bplace":     "\u0422\u0443\u0493\u0438\u043b\u0433\u0430\u043d \u0436\u043e\u0439\u0438",
        "nation":     "\u041c\u0438\u043b\u043b\u0430\u0442\u0438",
        "party":      "\u041f\u0430\u0440\u0442\u0438\u044f\u0432\u0438\u0439\u043b\u0438\u0433\u0438",
        "edu":        "\u041c\u0430\u044a\u043b\u0443\u043c\u043e\u0442\u0438",
        "grad":       "\u049a\u0430\u0439\u0441\u0438 \u043e\u043b\u0438\u0439 \u043c\u0430\u043a\u0442\u0430\u0431\u043d\u0438, \u049b\u0430\u0447\u043e\u043d \u0442\u0430\u043c\u043e\u043c\u043b\u0430\u0433\u0430\u043d",
        "spec":       "\u041c\u0443\u0442\u0430\u0445\u0430\u0441\u0441\u0438\u0441\u043b\u0438\u0433\u0438",
        "degree":     "\u0418\u043b\u043c\u0438\u0439 \u0434\u0430\u0440\u0430\u0436\u0430\u0441\u0438",
        "stitle":     "\u0418\u043b\u043c\u0438\u0439 \u0443\u043d\u0432\u043e\u043d\u0438",
        "langs":      "\u049a\u0430\u0439\u0441\u0438 \u0447\u0435\u0442 \u0442\u0438\u043b\u043b\u0430\u0440\u0438\u043d\u0438 \u0431\u0438\u043b\u0430\u0434\u0438",
        "military":   "\u04b2\u0430\u0440\u0431\u0438\u0439 \u0443\u043d\u0432\u043e\u043d\u0438",
        "awards":     "\u0414\u0430\u0432\u043b\u0430\u0442 \u043c\u0443\u043a\u043e\u0444\u043e\u0442\u043b\u0430\u0440\u0438",
        "deputy":     "\u0414\u0435\u043f\u0443\u0442\u0430\u0442\u043c\u0438 \u0451\u043a\u0438 \u0431\u043e\u0448\u049b\u0430 \u043e\u0440\u0433\u0430\u043d\u043b\u0430\u0440 \u0430\u044a\u0437\u043e\u0441\u0438\u043c\u0438",
        "work_title": "\u041c\u0415\u04b2\u041d\u0410\u0422 \u0424\u0410\u041e\u041b\u0418\u042f\u0422\u0418",
        "yillar":     "\u0419\u0438\u043b\u043b\u0430\u0440",
        "lavozim":    "\u0418\u0448 \u0436\u043e\u0439\u0438 \u0432\u0430 \u043b\u0430\u0432\u043e\u0437\u0438\u043c\u0438",
        "rel_title":  "\u041d\u0418\u041d\u0413 \u042f\u049a\u0418\u041d \u049a\u0410\u0420\u0418\u041d\u0414\u041e\u0428\u041b\u0410\u0420\u0418 \u04b2\u0410\u049a\u0418\u0414\u0410 \u041c\u0410\u042a\u041b\u0423\u041c\u041e\u0422",
        "rel_kin":    "\u049a\u0430\u0440\u0438\u043d\u0434\u043e\u0448\u043b\u0438\u0433\u0438",
        "rel_fish":   "\u0424.\u0418.\u0428.",
        "rel_birth":  "\u0422\u0443\u0493\u0438\u043b\u0433\u0430\u043d \u0439\u0438\u043b\u0438 \u0432\u0430 \u0436\u043e\u0439\u0438",
        "rel_work":   "\u0418\u0448 \u0436\u043e\u0439\u0438 \u0432\u0430 \u043b\u0430\u0432\u043e\u0437\u0438\u043c\u0438",
        "rel_addr":   "\u042f\u0448\u0430\u0448 \u043c\u0430\u043d\u0437\u0438\u043b\u0438",
        "photo":      "[\u0421\u0443\u0440\u0430\u0442]",
        "ru_prefix":  "",
    },
    "en": {
        "title":      "C U R R I C U L U M   V I T A E",
        "fullname":   "Full Name",
        "bdate":      "Date of birth",
        "bplace":     "Place of birth",
        "nation":     "Nationality",
        "party":      "Party membership",
        "edu":        "Education",
        "grad":       "University / school graduated from",
        "spec":       "Specialty",
        "degree":     "Academic degree",
        "stitle":     "Academic title",
        "langs":      "Foreign languages",
        "military":   "Military rank",
        "awards":     "State awards",
        "deputy":     "Is a deputy or member of elected bodies",
        "work_title": "WORK EXPERIENCE",
        "yillar":     "Years",
        "lavozim":    "Position and Workplace",
        "rel_title":  "'S CLOSE RELATIVES",
        "rel_kin":    "Relationship",
        "rel_fish":   "Full Name",
        "rel_birth":  "Year and Place of Birth",
        "rel_work":   "Workplace and Position",
        "rel_addr":   "Home Address",
        "photo":      "[Photo]",
        "ru_prefix":  "",
    },
    "ru": {
        "title":      "\u041e \u0411 \u042a \u0415 \u041a \u0422 \u0418 \u0412 \u041a \u0410",
        "fullname":   "\u0424\u0430\u043c\u0438\u043b\u0438\u044f, \u0438\u043c\u044f, \u043e\u0442\u0447\u0435\u0441\u0442\u0432\u043e",
        "bdate":      "\u0413\u043e\u0434, \u0447\u0438\u0441\u043b\u043e \u0438 \u043c\u0435\u0441\u044f\u0446 \u0440\u043e\u0436\u0434\u0435\u043d\u0438\u044f",
        "bplace":     "\u041c\u0435\u0441\u0442\u043e \u0440\u043e\u0436\u0434\u0435\u043d\u0438\u044f",
        "nation":     "\u041d\u0430\u0446\u0438\u043e\u043d\u0430\u043b\u044c\u043d\u043e\u0441\u0442\u044c",
        "party":      "\u041f\u0430\u0440\u0442\u0438\u0439\u043d\u043e\u0441\u0442\u044c",
        "edu":        "\u041e\u0431\u0440\u0430\u0437\u043e\u0432\u0430\u043d\u0438\u0435",
        "grad":       "\u041a\u0430\u043a\u043e\u0435 \u0432\u044b\u0441\u0448\u0435\u0435 \u0443\u0447\u0435\u0431\u043d\u043e\u0435 \u0437\u0430\u0432\u0435\u0434\u0435\u043d\u0438\u0435 \u043e\u043a\u043e\u043d\u0447\u0438\u043b(\u0430) \u0438 \u043a\u043e\u0433\u0434\u0430",
        "spec":       "\u0421\u043f\u0435\u0446\u0438\u0430\u043b\u044c\u043d\u043e\u0441\u0442\u044c",
        "degree":     "\u0423\u0447\u0451\u043d\u0430\u044f \u0441\u0442\u0435\u043f\u0435\u043d\u044c",
        "stitle":     "\u0423\u0447\u0451\u043d\u043e\u0435 \u0437\u0432\u0430\u043d\u0438\u0435",
        "langs":      "\u041a\u0430\u043a\u0438\u043c\u0438 \u0438\u043d\u043e\u0441\u0442\u0440\u0430\u043d\u043d\u044b\u043c\u0438 \u044f\u0437\u044b\u043a\u0430\u043c\u0438 \u0432\u043b\u0430\u0434\u0435\u0435\u0442",
        "military":   "\u0412\u043e\u0438\u043d\u0441\u043a\u043e\u0435 \u0437\u0432\u0430\u043d\u0438\u0435",
        "awards":     "\u0413\u043e\u0441\u0443\u0434\u0430\u0440\u0441\u0442\u0432\u0435\u043d\u043d\u044b\u0435 \u043d\u0430\u0433\u0440\u0430\u0434\u044b",
        "deputy":     "\u042f\u0432\u043b\u044f\u0435\u0442\u0441\u044f \u043b\u0438 \u0434\u0435\u043f\u0443\u0442\u0430\u0442\u043e\u043c \u0438\u043b\u0438 \u0447\u043b\u0435\u043d\u043e\u043c \u0434\u0440\u0443\u0433\u0438\u0445 \u0432\u044b\u0431\u043e\u0440\u043d\u044b\u0445 \u043e\u0440\u0433\u0430\u043d\u043e\u0432",
        "work_title": "\u0422\u0420\u0423\u0414\u041e\u0412\u0410\u042f \u0414\u0415\u042f\u0422\u0415\u041b\u042c\u041d\u041e\u0421\u0422\u042c",
        "yillar":     "\u0413\u043e\u0434\u044b",
        "lavozim":    "\u041c\u0435\u0441\u0442\u043e \u0440\u0430\u0431\u043e\u0442\u044b \u0438 \u0434\u043e\u043b\u0436\u043d\u043e\u0441\u0442\u044c",
        "rel_title":  " \u041e \u0411\u041b\u0418\u0417\u041a\u0418\u0425 \u0420\u041e\u0414\u0421\u0422\u0412\u0415\u041d\u041d\u0418\u041a\u0410\u0425",
        "rel_kin":    "\u0421\u0442\u0435\u043f\u0435\u043d\u044c \u0440\u043e\u0434\u0441\u0442\u0432\u0430",
        "rel_fish":   "\u0424.\u0418.\u041e.",
        "rel_birth":  "\u0413\u043e\u0434 \u0438 \u043c\u0435\u0441\u0442\u043e \u0440\u043e\u0436\u0434\u0435\u043d\u0438\u044f",
        "rel_work":   "\u041c\u0435\u0441\u0442\u043e \u0440\u0430\u0431\u043e\u0442\u044b \u0438 \u0434\u043e\u043b\u0436\u043d\u043e\u0441\u0442\u044c",
        "rel_addr":   "\u041c\u0435\u0441\u0442\u043e \u0436\u0438\u0442\u0435\u043b\u044c\u0441\u0442\u0432\u0430",
        "photo":      "[\u0424\u043e\u0442\u043e]",
        "ru_prefix":  "\u0421\u0412\u0415\u0414\u0415\u041d\u0418\u042f",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# OBYEKTIVKA DOCX
# ─────────────────────────────────────────────────────────────────────────────

def generate_obyektivka_docx(data: dict, output_dir: str = "temp") -> str:
    """
    Generate a multilingual Ma'lumotnoma (Obyektivka) DOCX.
    Language is read from data['lang'] (uz_lat | uz_cyr | en | ru).
    """
    os.makedirs(output_dir, exist_ok=True)

    lang = data.get("lang", "uz_lat")
    if lang not in _OBY_LABELS:
        lang = "uz_lat"
    ll = _OBY_LABELS[lang]

    safe_name = data.get("fullname", "unknown").replace(" ", "_").replace("/", "_")
    filepath = os.path.join(output_dir, f"obyektivka_{safe_name}_@DastyorAiBot.docx")

    doc = Document()
    _set_narrow_margins(doc)
    pw = _page_width(doc)

    # ── TITLE ──────────────────────────────────────────────────────────
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _styled_run(title_p, ll["title"], bold=True, size_pt=14, font_name="Times New Roman")

    # ── HEADER TABLE  (photo | personal data) ──────────────────────────
    hdr_tbl = doc.add_table(rows=1, cols=2)
    hdr_tbl.style = "Table Grid"
    hdr_tbl.autofit = False
    _set_col_width_pct(hdr_tbl, pw, [30, 70])

    photo_cell = hdr_tbl.cell(0, 0)
    photo_cell.text = ""
    p_photo = photo_cell.paragraphs[0]
    p_photo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _styled_run(p_photo, ll["photo"], italic=True, size_pt=9,
                font_name="Times New Roman",
                color=RGBColor(0x88, 0x88, 0x88))

    info_cell = hdr_tbl.cell(0, 1)
    info_cell.text = ""

    def _add_info_line(label: str, value: str):
        ip = info_cell.add_paragraph()
        _styled_run(ip, f"{label}: ", bold=True, size_pt=10)
        _styled_run(ip, value or "—", bold=False, size_pt=10)

    _add_info_line(ll["fullname"],  data.get("fullname", ""))
    _add_info_line(ll["bdate"],     data.get("birthdate", ""))
    _add_info_line(ll["bplace"],    data.get("birthplace", ""))
    _add_info_line(ll["nation"],    data.get("nation", ""))
    _add_info_line(ll["party"],     data.get("party", ""))
    _add_info_line(ll["edu"],       data.get("education", ""))
    _add_info_line(ll["grad"],      data.get("graduated", ""))
    _add_info_line(ll["spec"],      data.get("specialty", ""))
    _add_info_line(ll["degree"],    data.get("degree", ""))
    _add_info_line(ll["stitle"],    data.get("scientific_title", ""))
    _add_info_line(ll["langs"],     data.get("languages", ""))
    _add_info_line(ll["military"],  data.get("military_rank", ""))
    _add_info_line(ll["awards"],    data.get("awards", ""))
    _add_info_line(ll["deputy"],    data.get("deputy", ""))

    doc.add_paragraph()

    # ── WORK EXPERIENCE ────────────────────────────────────────────────
    sec_p = doc.add_paragraph()
    sec_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _styled_run(sec_p, ll["work_title"], bold=True, size_pt=11)

    work_tbl = doc.add_table(rows=1, cols=2)
    work_tbl.style = "Table Grid"
    work_tbl.autofit = False
    _set_col_width_pct(work_tbl, pw, [25, 75])

    hdr = work_tbl.rows[0].cells
    for cell, label in zip(hdr, [ll["yillar"], ll["lavozim"]]):
        cell.text = ""
        hp = cell.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _styled_run(hp, label, bold=True, size_pt=10)
        _set_cell_shading(cell, "D9D9D9")

    works = data.get("work_experience", [])
    if isinstance(works, list):
        for work in works:
            row = work_tbl.add_row().cells
            row[0].text = work.get("year", "") or work.get("years", "")
            row[1].text = work.get("position", "") or work.get("desc", "")
            for c in row:
                for p in c.paragraphs:
                    for r in p.runs:
                        r.font.size = Pt(10)
                        r.font.name = "Times New Roman"

    doc.add_paragraph()

    # ── RELATIVES TABLE ────────────────────────────────────────────────
    fname = (data.get("fullname", "").split(" ")[0] or "Shaxs").upper()
    rel_sec_p = doc.add_paragraph()
    rel_sec_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if lang == "ru":
        rel_headline = f"{ll['ru_prefix']}{ll['rel_title']}"
    else:
        rel_headline = f"{fname}{ll['rel_title']}"
    _styled_run(rel_sec_p, rel_headline, bold=True, size_pt=11)

    rel_tbl = doc.add_table(rows=1, cols=5)
    rel_tbl.style = "Table Grid"
    rel_tbl.autofit = False
    _set_col_width_pct(rel_tbl, pw, [18, 22, 18, 22, 20])

    rel_headers = [
        ll["rel_kin"], ll["rel_fish"], ll["rel_birth"],
        ll["rel_work"], ll["rel_addr"]
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
                rel.get("degree", "") or rel.get("role", ""),
                rel.get("fullname", "") or rel.get("name", ""),
                rel.get("birth_year_place", "") or rel.get("birth", ""),
                rel.get("work_place", "") or rel.get("work", ""),
                rel.get("address", "") or rel.get("addr", ""),
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
    Generate a styled CV DOCX matching one of eight templates.
    data['lang'] controls section headings language (uz_lat | uz_cyr | en | ru).
    """
    os.makedirs(output_dir, exist_ok=True)

    safe_name = data.get("name", "unknown").replace(" ", "_").replace("/", "_")
    template = data.get("template", "minimal").lower()
    filepath = os.path.join(output_dir, f"cv_{safe_name}_{template}_@DastyorAiBot.docx")

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
    works = data.get("works", []) or data.get("work_experience", [])
    edus = data.get("education_list", []) or []
    skills_raw: str = data.get("skills", "") or ""
    skills = [s.strip() for s in skills_raw.replace(",", "\n").splitlines() if s.strip()]

    # ── Multilingual section labels ─────────────────────────────────────
    _CV_SEC = {
        "uz_lat": {"about": "Haqida",    "exp": "Ish Tajribasi", "edu": "Ta'lim",      "skills": "Ko'nikmalar"},
        "uz_cyr": {"about": "Ҳақида",    "exp": "Иш Тажрибаси", "edu": "Таълим",       "skills": "Кўникмалар"},
        "en":     {"about": "About",     "exp": "Experience",    "edu": "Education",    "skills": "Skills"},
        "ru":     {"about": "О себе",    "exp": "Опыт работы",   "edu": "Образование",  "skills": "Навыки"},
    }
    lang = data.get("lang", "uz_lat")
    if lang not in _CV_SEC:
        lang = "uz_lat"
    _sec = _CV_SEC[lang]

    # ── NAME / TITLE header ────────────────────────────────────────────
    _heading(data.get("name", ""), level=0,
             align=WD_ALIGN_PARAGRAPH.CENTER if template != "split" else WD_ALIGN_PARAGRAPH.LEFT)

    spec_p = doc.add_paragraph()
    spec_p.alignment = WD_ALIGN_PARAGRAPH.CENTER if template != "split" else WD_ALIGN_PARAGRAPH.LEFT
    _styled_run(spec_p, data.get("spec", ""),
                italic=True, size_pt=12, font_name=FONT)

    doc.add_paragraph()  # spacer

    # ── CONTACT INFO ───────────────────────────────────────────────────
    contact_parts = []
    if data.get("phone"):
        contact_parts.append(f"📞 {data['phone']}")
    if data.get("email"):
        contact_parts.append(f"✉️ {data['email']}")
    if data.get("loc"):
        contact_parts.append(f"📍 {data['loc']}")

    if contact_parts:
        cp = doc.add_paragraph()
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER if template == "minimal" else WD_ALIGN_PARAGRAPH.LEFT
        _styled_run(cp, "  •  ".join(contact_parts), size_pt=9.5, font_name=FONT)

    doc.add_paragraph()

    # ── ABOUT ─────────────────────────────────────────────────────────
    about = data.get("about", "")
    if about:
        _heading(_sec["about"].upper(), level=1, underline=True)
        _para(about, size=10.5)
        doc.add_paragraph()

    # ── WORK EXPERIENCE ───────────────────────────────────────────────
    if works:
        _heading(_sec["exp"].upper(), level=1, underline=True)
        for w in works:
            from_y = w.get("f", "") or w.get("from", "") or w.get("year", "")
            to_y = w.get("t", "") or w.get("to", "")
            desc = w.get("d", "") or w.get("position", "") or w.get("desc", "") or w.get("description", "")
            title = w.get("title", "") or w.get("pos", "")
            company = w.get("company", "") or w.get("co", "")
            period = f"{from_y} – {to_y}" if to_y else from_y
            if not period and w.get("date"):
                period = w["date"]
            exp_p = doc.add_paragraph()
            _styled_run(exp_p, f"{title or period}", bold=True, size_pt=10, font_name=FONT)
            if company:
                _styled_run(exp_p, f"\n{company}", italic=True, size_pt=9.5, font_name=FONT)
            if period and title:
                _styled_run(exp_p, f"\n{period}", size_pt=9, font_name=FONT)
            if desc:
                _styled_run(exp_p, f"\n{desc}", size_pt=10, font_name=FONT)
        doc.add_paragraph()

    # ── EDUCATION ─────────────────────────────────────────────────────
    if edus or data.get("edu") or data.get("grad"):
        _heading(_sec["edu"].upper(), level=1, underline=True)
        if edus:
            for edu in edus:
                ep = doc.add_paragraph()
                _styled_run(ep, edu.get("title", "") or edu.get("name", ""), bold=True, size_pt=10, font_name=FONT)
                details = []
                if edu.get("date") or edu.get("year"):
                    details.append(edu.get("date") or edu.get("year"))
                if edu.get("company") or edu.get("field"):
                    details.append(edu.get("company") or edu.get("field"))
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
        _heading(_sec["skills"].upper(), level=1, underline=True)
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
