"""
Document Generator Service — DASTYOR AI
Generates professionally formatted DOCX files for Obyektivka and CV.
Supports 4 languages: uz_lat | uz_cyr | en | ru

Design matches the HTML preview template exactly:
  - Navy blue (#1A3A6B) accent headers
  - Zebra-striped tables
  - Name-block card style
  - Consistent typography (Times New Roman)
"""

import io
import os
import logging
from typing import Any

from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ROW_HEIGHT_RULE
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Design constants  (match HTML template)
# ─────────────────────────────────────────────────────────────────────────────

NAVY        = RGBColor(0x1A, 0x3A, 0x6B)   # #1A3A6B  – accent / header bg
NAVY_HEX    = "1A3A6B"
WHITE       = RGBColor(0xFF, 0xFF, 0xFF)
WHITE_HEX   = "FFFFFF"
LIGHT_BLUE_HEX = "F0F4FB"                  # name-block / section-header bg
STRIPE_HEX  = "F8F9FC"                     # even-row zebra stripe
LABEL_CLR   = RGBColor(0x4A, 0x5A, 0x80)  # field label colour
BORDER_HEX  = "C5D0E4"                     # cell border colour
DARK_TEXT   = RGBColor(0x1A, 0x1A, 0x2E)  # body text

FONT_BODY   = "Times New Roman"
FONT_SIZE   = 10.5   # pt  body
FONT_LBL    = 8.5    # pt  label
FONT_TITLE  = 15.0   # pt  document title
FONT_SECT   = 10.5   # pt  section header
FONT_NAME   = 14.0   # pt  person name
FONT_EXP    = 10.0   # pt  table body
FONT_REL    = 9.0    # pt  relatives table body

MARGIN_CM   = 1.5    # top
MARGIN_B_CM = 1.0    # bottom
MARGIN_L_CM = 2.0    # left
MARGIN_R_CM = 1.0    # right


# ─────────────────────────────────────────────────────────────────────────────
# Low-level XML helpers
# ─────────────────────────────────────────────────────────────────────────────

def _set_margins(doc: Document) -> None:
    for section in doc.sections:
        section.top_margin    = Cm(MARGIN_CM)
        section.bottom_margin = Cm(MARGIN_B_CM)
        section.left_margin   = Cm(MARGIN_L_CM)
        section.right_margin  = Cm(MARGIN_R_CM)


def _page_width(doc: Document) -> int:
    """Usable page width in EMU."""
    sec = doc.sections[0]
    return sec.page_width - sec.left_margin - sec.right_margin


def _run(para, text: str, bold=False, italic=False,
         size_pt: float = FONT_SIZE,
         font_name: str = FONT_BODY,
         color: RGBColor = None):
    r = para.add_run(text)
    r.bold          = bold
    r.italic        = italic
    r.font.name     = font_name
    r.font.size     = Pt(size_pt)
    if color:
        r.font.color.rgb = color
    return r


def _cell_shading(cell, fill_hex: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  fill_hex.lstrip("#"))
    tc_pr.append(shd)


def _cell_border(cell, color_hex: str = BORDER_HEX) -> None:
    """Set all four borders of a cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_borders = OxmlElement("w:tcBorders")
    for side in ("top", "left", "bottom", "right"):
        border = OxmlElement(f"w:{side}")
        border.set(qn("w:val"),   "single")
        border.set(qn("w:sz"),    "4")   # 0.5pt
        border.set(qn("w:space"), "0")
        border.set(qn("w:color"), color_hex.lstrip("#"))
        tc_borders.append(border)
    tc_pr.append(tc_borders)


def _top_border_only(cell, color_hex: str = NAVY_HEX, sz: str = "16") -> None:
    """Add only top border to a cell (section title effect)."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_borders = OxmlElement("w:tcBorders")
    top = OxmlElement("w:top")
    top.set(qn("w:val"),   "single")
    top.set(qn("w:sz"),    sz)       # e.g. "16" = 2pt
    top.set(qn("w:space"), "0")
    top.set(qn("w:color"), color_hex.lstrip("#"))
    tc_borders.append(top)
    # Remove other borders
    for side in ("left", "bottom", "right"):
        b = OxmlElement(f"w:{side}")
        b.set(qn("w:val"), "none")
        tc_borders.append(b)
    tc_pr.append(tc_borders)


def _set_col_widths(table, page_width_emu: int, pcts: list) -> None:
    for col_idx, pct in enumerate(pcts):
        w = int(page_width_emu * pct / 100)
        for cell in table.columns[col_idx].cells:
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            tcW = OxmlElement("w:tcW")
            tcW.set(qn("w:w"),    str(w))
            tcW.set(qn("w:type"), "dxa")
            tcPr.append(tcW)


def _remove_table_borders(table) -> None:
    """Remove outer/inner table borders (rely on cell borders only)."""
    tbl = table._tbl
    tblPr = tbl.find(qn("w:tblPr"))
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        tbl.insert(0, tblPr)
    tblBorders = OxmlElement("w:tblBorders")
    for side in ("top","left","bottom","right","insideH","insideV"):
        b = OxmlElement(f"w:{side}")
        b.set(qn("w:val"),   "none")
        b.set(qn("w:sz"),    "0")
        b.set(qn("w:space"), "0")
        b.set(qn("w:color"), "auto")
        tblBorders.append(b)
    tblPr.append(tblBorders)


def _para_spacing(para, before_pt=0, after_pt=0, line_rule=None):
    pPr = para._p.get_or_add_pPr()
    spacing = OxmlElement("w:spacing")
    spacing.set(qn("w:before"), str(int(before_pt * 20)))
    spacing.set(qn("w:after"),  str(int(after_pt  * 20)))
    if line_rule:
        spacing.set(qn("w:line"),     line_rule[0])
        spacing.set(qn("w:lineRule"), line_rule[1])
    pPr.append(spacing)


# ─────────────────────────────────────────────────────────────────────────────
# Multilingual labels
# ─────────────────────────────────────────────────────────────────────────────

_OBY_LABELS = {
    "uz_lat": {
        "title":      "MA'LUMOTNOMA",
        "name_label": "F.I.SH.",
        "fullname":   "Familiya, ismi, sharifi",
        "bdate":      "Tug'ilgan yili, kuni va oyi",
        "bplace":     "Tug'ilgan joyi",
        "nation":     "Millati",
        "party":      "Partiyaviyligi",
        "edu":        "Ma'lumoti",
        "grad":       "Qaysi oliy (o'rta) maktabni tamomlagan",
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
        "rel_title":  "YAQIN QARINDOSHLARI HAQIDA MA'LUMOT",
        "rel_kin":    "Qarindoshligi",
        "rel_fish":   "F.I.SH.",
        "rel_birth":  "Tug'ilgan yili va joyi",
        "rel_work":   "Ish joyi va lavozimi",
        "rel_addr":   "Yashash manzili",
        "photo":      "[Fotosurat 4×6]",
        "ru_prefix":  "",
        "none":       "—",
    },
    "uz_cyr": {
        "title":      "МАЪЛУМОТНОМА",
        "name_label": "Ф.И.Ш.",
        "fullname":   "Фамилия, исми, шарифи",
        "bdate":      "Туғилган йили, куни ва ойи",
        "bplace":     "Туғилган жойи",
        "nation":     "Миллати",
        "party":      "Партиявийлиги",
        "edu":        "Маълумоти",
        "grad":       "Қайси олий мактабни тамомлаган",
        "spec":       "Мутахассислиги",
        "degree":     "Илмий даражаси",
        "stitle":     "Илмий унвони",
        "langs":      "Қайси чет тилларини билади",
        "military":   "Ҳарбий унвони",
        "awards":     "Давлат мукофотлари",
        "deputy":     "Депутатми ёки бошқа сайланадиган органлар аъзосими",
        "work_title": "МЕҲНАТ ФАОЛИЯТИ",
        "yillar":     "Йиллар",
        "lavozim":    "Иш жойи ва лавозими",
        "rel_title":  "ЯҚИН ҚАРИНДОШЛАРИ ҲАҚИДА МАЪЛУМОТ",
        "rel_kin":    "Қариндошлиги",
        "rel_fish":   "Ф.И.Ш.",
        "rel_birth":  "Туғилган йили ва жойи",
        "rel_work":   "Иш жойи ва лавозими",
        "rel_addr":   "Яшаш манзили",
        "photo":      "[Сурат 4×6]",
        "ru_prefix":  "",
        "none":       "—",
    },
    "en": {
        "title":      "CURRICULUM VITAE",
        "name_label": "Full Name",
        "fullname":   "Full Name",
        "bdate":      "Date of birth",
        "bplace":     "Place of birth",
        "nation":     "Nationality",
        "party":      "Party membership",
        "edu":        "Education",
        "grad":       "University graduated from",
        "spec":       "Specialty",
        "degree":     "Academic degree",
        "stitle":     "Academic title",
        "langs":      "Foreign languages",
        "military":   "Military rank",
        "awards":     "State awards",
        "deputy":     "Is a deputy or member of elected bodies",
        "work_title": "WORK EXPERIENCE",
        "yillar":     "Period",
        "lavozim":    "Position & Workplace",
        "rel_title":  "CLOSE RELATIVES INFORMATION",
        "rel_kin":    "Relationship",
        "rel_fish":   "Full Name",
        "rel_birth":  "Year and Place of Birth",
        "rel_work":   "Workplace and Position",
        "rel_addr":   "Home Address",
        "photo":      "[Photo 4×6]",
        "ru_prefix":  "",
        "none":       "—",
    },
    "ru": {
        "title":      "ОБЪЕКТИВКА",
        "name_label": "Ф.И.О.",
        "fullname":   "Фамилия, имя, отчество",
        "bdate":      "Год, число и месяц рождения",
        "bplace":     "Место рождения",
        "nation":     "Национальность",
        "party":      "Партийность",
        "edu":        "Образование",
        "grad":       "Какое высшее учебное заведение окончил(а)",
        "spec":       "Специальность",
        "degree":     "Учёная степень",
        "stitle":     "Учёное звание",
        "langs":      "Какими иностранными языками владеет",
        "military":   "Воинское звание",
        "awards":     "Государственные награды",
        "deputy":     "Является ли депутатом или членом других выборных органов",
        "work_title": "ТРУДОВАЯ ДЕЯТЕЛЬНОСТЬ",
        "yillar":     "Годы",
        "lavozim":    "Место работы и должность",
        "rel_title":  "СВЕДЕНИЯ О БЛИЗКИХ РОДСТВЕННИКАХ",
        "rel_kin":    "Степень родства",
        "rel_fish":   "Ф.И.О.",
        "rel_birth":  "Год и место рождения",
        "rel_work":   "Место работы и должность",
        "rel_addr":   "Место жительства",
        "photo":      "[Фото 4×6]",
        "ru_prefix":  "СВЕДЕНИЯ",
        "none":       "—",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# OBYEKTIVKA DOCX  — matching HTML template design
# ─────────────────────────────────────────────────────────────────────────────

def generate_obyektivka_docx(data: dict, output_dir: str = "temp") -> str:
    """
    Generate a professionally styled Obyektivka DOCX.
    Design mirrors the HTML preview template exactly:
      - Navy blue accent bars and section headers
      - Name-block card with left border
      - Label (small caps) + value layout
      - Zebra-striped tables with dark navy headers
    """
    os.makedirs(output_dir, exist_ok=True)

    lang = data.get("lang", "uz_lat")
    if lang not in _OBY_LABELS:
        lang = "uz_lat"
    ll = _OBY_LABELS[lang]

    safe_name = (data.get("fullname", "unknown") or "unknown").replace(" ", "_").replace("/", "_")
    filepath  = os.path.join(output_dir, f"obyektivka_{safe_name}_@DastyorAiBot.docx")

    doc = Document()
    _set_margins(doc)

    # Remove default paragraph spacing
    style = doc.styles["Normal"]
    style.font.name = FONT_BODY
    style.font.size = Pt(FONT_SIZE)
    style.paragraph_format.space_before = Pt(0)
    style.paragraph_format.space_after  = Pt(0)

    pw = _page_width(doc)

    # ── 1. TOP ACCENT BAR (navy full-width line) ──────────────────────────
    bar_tbl = doc.add_table(rows=1, cols=1)
    _remove_table_borders(bar_tbl)
    bar_cell = bar_tbl.cell(0, 0)
    _cell_shading(bar_cell, NAVY_HEX)
    bar_cell.width = pw
    bar_p = bar_cell.paragraphs[0]
    bar_p.text = ""
    bar_p.paragraph_format.space_before = Pt(0)
    bar_p.paragraph_format.space_after  = Pt(0)
    # Set row height to 4pt (matches 4px bar in HTML)
    tr = bar_tbl.rows[0]._tr
    trPr = tr.get_or_add_trPr()
    trHeight = OxmlElement("w:trHeight")
    trHeight.set(qn("w:val"), "80")  # 80 twips ≈ ~4pt
    trHeight.set(qn("w:hRule"), "exact")
    trPr.append(trHeight)

    doc.add_paragraph()   # small spacer

    # ── 2. TITLE ─────────────────────────────────────────────────────────
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _para_spacing(title_p, before_pt=4, after_pt=2)
    tr = _run(title_p, ll["title"], bold=True, size_pt=FONT_TITLE, color=NAVY)
    # Letter-spacing via XML (w:spacing)
    rPr = tr._r.get_or_add_rPr()
    spacing_el = OxmlElement("w:spacing")
    spacing_el.set(qn("w:val"), "100")   # ~4px letter spacing
    rPr.append(spacing_el)

    # Thin decorative line under title (via paragraph border)
    _add_hr(doc, color_hex=NAVY_HEX, size=4, space=4)

    doc.add_paragraph()   # spacer

    # ── 3. HEADER: Name block (left) + Photo placeholder (right) ─────────
    hdr_tbl = doc.add_table(rows=1, cols=2)
    _remove_table_borders(hdr_tbl)
    hdr_tbl.autofit = False
    _set_col_widths(hdr_tbl, pw, [72, 28])

    # Left cell — name-block card
    name_cell = hdr_tbl.cell(0, 0)
    name_cell.text = ""
    _cell_shading(name_cell, LIGHT_BLUE_HEX)
    # Left bold border (4pt navy)
    _set_left_border(name_cell, NAVY_HEX, sz="32")  # 4pt
    _cell_border(name_cell, BORDER_HEX)

    name_p = name_cell.paragraphs[0]
    _para_spacing(name_p, before_pt=6, after_pt=2)
    name_p.paragraph_format.left_indent = Cm(0.3)

    # Label row
    lbl_p = name_cell.add_paragraph()
    _para_spacing(lbl_p, before_pt=4, after_pt=1)
    lbl_p.paragraph_format.left_indent = Cm(0.3)
    _run(lbl_p, ll["name_label"].upper(), bold=False,
         size_pt=FONT_LBL, color=LABEL_CLR)

    # Name value
    val_p = name_cell.add_paragraph()
    _para_spacing(val_p, before_pt=2, after_pt=6)
    val_p.paragraph_format.left_indent = Cm(0.3)
    _run(val_p, (data.get("fullname") or ll["none"]).upper(),
         bold=True, size_pt=FONT_NAME, color=DARK_TEXT)

    # Right cell — photo placeholder
    photo_cell = hdr_tbl.cell(0, 1)
    photo_cell.text = ""
    _cell_shading(photo_cell, LIGHT_BLUE_HEX)
    _cell_border(photo_cell, NAVY_HEX)
    ph_p = photo_cell.paragraphs[0]
    ph_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _para_spacing(ph_p, before_pt=20, after_pt=20)
    _run(ph_p, ll["photo"], italic=True, size_pt=9, color=LABEL_CLR)

    doc.add_paragraph()   # spacer

    # ── 4. PERSONAL INFO TABLE ────────────────────────────────────────────
    # 6 rows × 2 columns (last row spans full width for deputy)
    info_rows = [
        (ll["bdate"],   data.get("birthdate", "")  or ll["none"],
         ll["bplace"],  data.get("birthplace", "") or ll["none"]),
        (ll["nation"],  data.get("nation", "")     or ll["none"],
         ll["party"],   data.get("party", "")      or ll["none"]),
        (ll["edu"],     data.get("education", "")  or ll["none"],
         ll["grad"],    data.get("graduated", "")  or ll["none"]),
        (ll["spec"],    data.get("specialty", "")  or ll["none"],
         ll["degree"],  data.get("degree", "")     or ll["none"]),
        (ll["stitle"],  data.get("scientific_title", "") or ll["none"],
         ll["langs"],   data.get("languages", "")  or ll["none"]),
        (ll["military"],data.get("military_rank", "") or ll["none"],
         ll["awards"],  data.get("awards", "")     or ll["none"]),
    ]

    info_tbl = doc.add_table(rows=len(info_rows) + 1, cols=2)
    _remove_table_borders(info_tbl)
    info_tbl.autofit = False
    _set_col_widths(info_tbl, pw, [50, 50])

    for row_idx, row_data in enumerate(info_rows):
        lbl1, val1, lbl2, val2 = row_data
        is_even = (row_idx % 2 == 1)
        bg = STRIPE_HEX if is_even else "FFFFFF"

        for col_idx, (lbl, val) in enumerate([(lbl1, val1), (lbl2, val2)]):
            cell = info_tbl.cell(row_idx, col_idx)
            cell.text = ""
            _cell_shading(cell, bg)
            _cell_border(cell, BORDER_HEX)

            lp = cell.paragraphs[0]
            _para_spacing(lp, before_pt=4, after_pt=1)
            lp.paragraph_format.left_indent = Cm(0.2)
            _run(lp, lbl.upper(), bold=True, size_pt=FONT_LBL, color=LABEL_CLR)

            vp = cell.add_paragraph()
            _para_spacing(vp, before_pt=1, after_pt=5)
            vp.paragraph_format.left_indent = Cm(0.2)
            _run(vp, val, bold=False, size_pt=FONT_SIZE, color=DARK_TEXT)

    # Deputy row (full width, merged)
    dep_row_idx = len(info_rows)
    dep_cell = info_tbl.cell(dep_row_idx, 0)
    dep_cell2 = info_tbl.cell(dep_row_idx, 1)
    dep_cell.merge(dep_cell2)
    dep_cell.text = ""
    _cell_shading(dep_cell, "FFFFFF")
    _cell_border(dep_cell, BORDER_HEX)

    dp = dep_cell.paragraphs[0]
    _para_spacing(dp, before_pt=4, after_pt=1)
    dp.paragraph_format.left_indent = Cm(0.2)
    _run(dp, ll["deputy"].upper(), bold=True, size_pt=FONT_LBL, color=LABEL_CLR)

    dvp = dep_cell.add_paragraph()
    _para_spacing(dvp, before_pt=1, after_pt=5)
    dvp.paragraph_format.left_indent = Cm(0.2)
    _run(dvp, data.get("deputy", "") or ll["none"],
         bold=False, size_pt=FONT_SIZE, color=DARK_TEXT)

    doc.add_paragraph()  # spacer

    # ── 5. SECTION: WORK EXPERIENCE ───────────────────────────────────────
    _add_section_header(doc, pw, ll["work_title"])

    works = data.get("work_experience", [])
    if works and isinstance(works, list) and any(
        w.get("year") or w.get("years") or w.get("position") or w.get("desc")
        for w in works
    ):
        exp_tbl = doc.add_table(rows=1 + len(works), cols=2)
        _remove_table_borders(exp_tbl)
        exp_tbl.autofit = False
        _set_col_widths(exp_tbl, pw, [26, 74])

        # Header row
        for col_idx, label in enumerate([ll["yillar"], ll["lavozim"]]):
            hcell = exp_tbl.cell(0, col_idx)
            hcell.text = ""
            _cell_shading(hcell, NAVY_HEX)
            _cell_border(hcell, NAVY_HEX)
            hp = hcell.paragraphs[0]
            hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _para_spacing(hp, before_pt=4, after_pt=4)
            _run(hp, label, bold=True, size_pt=9.5, color=WHITE)

        # Data rows
        for i, work in enumerate(works):
            is_even = (i % 2 == 1)
            bg = STRIPE_HEX if is_even else "FFFFFF"
            year_val = work.get("year", "") or work.get("years", "") or ll["none"]
            pos_val  = work.get("position", "") or work.get("desc", "") or ll["none"]

            yr_cell  = exp_tbl.cell(i + 1, 0)
            pos_cell = exp_tbl.cell(i + 1, 1)

            for cell, val in [(yr_cell, year_val), (pos_cell, pos_val)]:
                cell.text = ""
                _cell_shading(cell, bg)
                _cell_border(cell, BORDER_HEX)
                cp = cell.paragraphs[0]
                _para_spacing(cp, before_pt=4, after_pt=4)
                cp.paragraph_format.left_indent = Cm(0.15)
                bold_yr = (cell is yr_cell)
                _run(cp, val, bold=bold_yr, size_pt=FONT_EXP,
                     color=NAVY if bold_yr else DARK_TEXT)
    else:
        ep = doc.add_paragraph()
        ep.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _para_spacing(ep, before_pt=4, after_pt=4)
        _run(ep, "—", italic=True, size_pt=FONT_EXP, color=LABEL_CLR)

    doc.add_paragraph()

    # ── 6. SECTION: RELATIVES ─────────────────────────────────────────────
    fname = (data.get("fullname", "") or "").split(" ")[0].upper()
    if lang == "ru":
        rel_headline = ll["ru_prefix"] + " " + ll["rel_title"]
    else:
        rel_headline = (fname + " " if fname else "") + ll["rel_title"]

    _add_section_header(doc, pw, rel_headline)

    relatives = data.get("relatives", [])
    if relatives and isinstance(relatives, list) and any(
        r.get("degree") or r.get("role") or r.get("fullname") or r.get("name")
        for r in relatives
    ):
        headers = [ll["rel_kin"], ll["rel_fish"], ll["rel_birth"],
                   ll["rel_work"],  ll["rel_addr"]]
        pcts    = [13, 20, 17, 28, 22]

        rel_tbl = doc.add_table(rows=1 + len(relatives), cols=5)
        _remove_table_borders(rel_tbl)
        rel_tbl.autofit = False
        _set_col_widths(rel_tbl, pw, pcts)

        # Header
        for col_idx, label in enumerate(headers):
            hcell = rel_tbl.cell(0, col_idx)
            hcell.text = ""
            _cell_shading(hcell, NAVY_HEX)
            _cell_border(hcell, NAVY_HEX)
            hp = hcell.paragraphs[0]
            hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _para_spacing(hp, before_pt=3, after_pt=3)
            _run(hp, label, bold=True, size_pt=8.5, color=WHITE)

        # Rows
        for i, rel in enumerate(relatives):
            is_even = (i % 2 == 1)
            bg = STRIPE_HEX if is_even else "FFFFFF"
            vals = [
                rel.get("degree", "") or rel.get("role", "")            or ll["none"],
                rel.get("fullname", "") or rel.get("name", "")          or ll["none"],
                rel.get("birth_year_place", "") or rel.get("birth", "") or ll["none"],
                rel.get("work_place", "") or rel.get("work", "")        or ll["none"],
                rel.get("address", "") or rel.get("addr", "")           or ll["none"],
            ]
            for col_idx, val in enumerate(vals):
                rcell = rel_tbl.cell(i + 1, col_idx)
                rcell.text = ""
                _cell_shading(rcell, bg)
                _cell_border(rcell, BORDER_HEX)
                rp = rcell.paragraphs[0]
                rp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                _para_spacing(rp, before_pt=3, after_pt=3)
                _run(rp, val, size_pt=FONT_REL, color=DARK_TEXT)
    else:
        ep = doc.add_paragraph()
        ep.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _para_spacing(ep, before_pt=4, after_pt=4)
        _run(ep, "—", italic=True, size_pt=FONT_EXP, color=LABEL_CLR)

    doc.save(filepath)
    logger.info(f"Obyektivka DOCX saved: {filepath}")
    return filepath


# ─────────────────────────────────────────────────────────────────────────────
# Component helpers
# ─────────────────────────────────────────────────────────────────────────────

def _add_hr(doc: Document, color_hex: str = NAVY_HEX,
            size: int = 4, space: int = 4) -> None:
    """Add a horizontal rule paragraph (bottom border only)."""
    hr_p = doc.add_paragraph()
    hr_p.paragraph_format.space_before = Pt(0)
    hr_p.paragraph_format.space_after  = Pt(space)
    pPr = hr_p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"),   "single")
    bottom.set(qn("w:sz"),    str(size))
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), color_hex.lstrip("#"))
    pBdr.append(bottom)
    pPr.append(pBdr)


def _set_left_border(cell, color_hex: str, sz: str = "32") -> None:
    """Set only the left border of a cell (card accent style)."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_borders = OxmlElement("w:tcBorders")
    left = OxmlElement("w:left")
    left.set(qn("w:val"),   "single")
    left.set(qn("w:sz"),    sz)
    left.set(qn("w:space"), "0")
    left.set(qn("w:color"), color_hex.lstrip("#"))
    tc_borders.append(left)
    tc_pr.append(tc_borders)


def _add_section_header(doc: Document, pw: int, title: str) -> None:
    """
    Add a section header matching the HTML .sect-title style:
      - Navy 2pt top border
      - Light blue background (#F0F4FB)
      - Navy bold text, centered, uppercase, with letter-spacing
      - Bottom navy thin border
    """
    s_tbl = doc.add_table(rows=1, cols=1)
    _remove_table_borders(s_tbl)
    s_tbl.autofit = False

    s_cell = s_tbl.cell(0, 0)
    s_cell.text = ""
    _cell_shading(s_cell, LIGHT_BLUE_HEX)

    # Top border: thick navy
    tc_pr = s_cell._tc.get_or_add_tcPr()
    tc_borders = OxmlElement("w:tcBorders")
    for side, sz_val in [("top", "24"), ("bottom", "8"), ("left", "0"), ("right", "0")]:
        b = OxmlElement(f"w:{side}")
        if sz_val == "0":
            b.set(qn("w:val"), "none")
        else:
            b.set(qn("w:val"),   "single")
            b.set(qn("w:sz"),    sz_val)
            b.set(qn("w:space"), "0")
            b.set(qn("w:color"), NAVY_HEX if side == "top" else BORDER_HEX)
        tc_borders.append(b)
    tc_pr.append(tc_borders)

    s_p = s_cell.paragraphs[0]
    s_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _para_spacing(s_p, before_pt=5, after_pt=5)
    sr = _run(s_p, title, bold=True, size_pt=FONT_SECT, color=NAVY)

    # Letter spacing
    rPr = sr._r.get_or_add_rPr()
    sc_el = OxmlElement("w:spacing")
    sc_el.set(qn("w:val"), "60")
    rPr.append(sc_el)

    # Spacing after section header
    after_p = doc.add_paragraph()
    _para_spacing(after_p, before_pt=0, after_pt=2)


# ─────────────────────────────────────────────────────────────────────────────
# CV DOCX  (unchanged from original — generates separate doc_generator output)
# ─────────────────────────────────────────────────────────────────────────────

def _set_narrow_margins(doc: Document, cm: float = 1.27) -> None:
    for section in doc.sections:
        section.top_margin    = Cm(cm)
        section.bottom_margin = Cm(cm)
        section.left_margin   = Cm(cm)
        section.right_margin  = Cm(cm)


def _page_width_narrow(doc: Document) -> int:
    sec = doc.sections[0]
    return sec.page_width - sec.left_margin - sec.right_margin


def _styled_run(paragraph, text: str, bold=False, italic=False,
                size_pt: float = 11, font_name: str = "Times New Roman",
                color: RGBColor | None = None):
    run = paragraph.add_run(text)
    run.bold       = bold
    run.italic     = italic
    run.font.name  = font_name
    run.font.size  = Pt(size_pt)
    if color:
        run.font.color.rgb = color
    return run


def _set_col_width_pct(table, page_width_emu: int, pcts: list) -> None:
    assert len(pcts) == len(table.columns)
    for col_idx, pct in enumerate(pcts):
        w = int(page_width_emu * pct / 100)
        for cell in table.columns[col_idx].cells:
            cell.width = w


def _set_cell_shading(cell, fill_hex: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  fill_hex)
    tc_pr.append(shd)


def generate_cv_docx(data: dict, output_dir: str = "temp") -> str:
    """
    Generate a styled CV DOCX matching one of eight templates.
    data['lang'] controls section headings language (uz_lat | uz_cyr | en | ru).
    """
    os.makedirs(output_dir, exist_ok=True)

    safe_name = data.get("name", "unknown").replace(" ", "_").replace("/", "_")
    template  = data.get("template", "minimal").lower()
    filepath  = os.path.join(output_dir, f"cv_{safe_name}_{template}_@DastyorAiBot.docx")

    doc = Document()
    _set_narrow_margins(doc, cm=1.5)
    pw = _page_width_narrow(doc)

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
        _styled_run(p, text, italic=italic, bold=bold, size_pt=size, font_name=FONT)
        return p

    works      = data.get("works", []) or data.get("work_experience", [])
    edus       = data.get("education_list", []) or []
    skills_raw = data.get("skills", "") or ""
    skills     = [s.strip() for s in skills_raw.replace(",", "\n").splitlines() if s.strip()]

    _CV_SEC = {
        "uz_lat": {"about": "Haqida",     "exp": "Ish Tajribasi", "edu": "Ta'lim",       "skills": "Ko'nikmalar"},
        "uz_cyr": {"about": "Ҳақида",     "exp": "Иш Тажрибаси", "edu": "Таълим",        "skills": "Кўникмалар"},
        "en":     {"about": "About",      "exp": "Experience",    "edu": "Education",     "skills": "Skills"},
        "ru":     {"about": "О себе",     "exp": "Опыт работы",   "edu": "Образование",   "skills": "Навыки"},
    }
    lang = data.get("lang", "uz_lat")
    if lang not in _CV_SEC:
        lang = "uz_lat"
    _sec = _CV_SEC[lang]

    _heading(data.get("name", ""), level=0,
             align=WD_ALIGN_PARAGRAPH.CENTER if template != "split" else WD_ALIGN_PARAGRAPH.LEFT)

    spec_p = doc.add_paragraph()
    spec_p.alignment = WD_ALIGN_PARAGRAPH.CENTER if template != "split" else WD_ALIGN_PARAGRAPH.LEFT
    _styled_run(spec_p, data.get("spec", "") or data.get("role", ""),
                italic=True, size_pt=12, font_name=FONT)

    doc.add_paragraph()

    contact_parts = []
    if data.get("phone"):  contact_parts.append(f"📞 {data['phone']}")
    if data.get("email"):  contact_parts.append(f"✉️ {data['email']}")
    if data.get("loc"):    contact_parts.append(f"📍 {data['loc']}")

    if contact_parts:
        cp = doc.add_paragraph()
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER if template == "minimal" else WD_ALIGN_PARAGRAPH.LEFT
        _styled_run(cp, "  •  ".join(contact_parts), size_pt=9.5, font_name=FONT)

    doc.add_paragraph()

    about = data.get("about", "")
    if about:
        _heading(_sec["about"].upper(), level=1, underline=True)
        _para(about, size=10.5)
        doc.add_paragraph()

    if works:
        _heading(_sec["exp"].upper(), level=1, underline=True)
        for w in works:
            from_y = w.get("f", "") or w.get("from", "") or w.get("year", "")
            to_y   = w.get("t", "") or w.get("to", "")
            desc   = w.get("d", "") or w.get("position", "") or w.get("desc", "") or w.get("description", "")
            title  = w.get("title", "") or w.get("pos", "")
            company= w.get("company", "") or w.get("co", "")
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

    if edus or data.get("edu") or data.get("grad"):
        _heading(_sec["edu"].upper(), level=1, underline=True)
        if edus:
            for edu in edus:
                ep = doc.add_paragraph()
                _styled_run(ep, edu.get("title", "") or edu.get("name", ""),
                            bold=True, size_pt=10, font_name=FONT)
                details = []
                if edu.get("date") or edu.get("year"):
                    details.append(edu.get("date") or edu.get("year"))
                if edu.get("company") or edu.get("field"):
                    details.append(edu.get("company") or edu.get("field"))
                if details:
                    _styled_run(ep, f"\n{', '.join(details)}", size_pt=9.5, font_name=FONT)
        else:
            edu_text  = data.get("edu", "")
            grad_text = data.get("grad", "")
            if edu_text:  _para(f"✓ {edu_text}", size=10.5)
            if grad_text: _para(f"✓ {grad_text}", size=10.5)
        doc.add_paragraph()

    if skills:
        _heading(_sec["skills"].upper(), level=1, underline=True)
        for sk in skills:
            sp = doc.add_paragraph(style="List Bullet")
            sp.paragraph_format.left_indent = Cm(0.5)
            _styled_run(sp, sk, size_pt=10, font_name=FONT)
        doc.add_paragraph()

    doc.save(filepath)
    logger.info(f"CV DOCX saved: {filepath}")
    return filepath


# ─────────────────────────────────────────────────────────────────────────────
# PDF conversion (platform-aware, graceful fallback)
# ─────────────────────────────────────────────────────────────────────────────

def convert_to_pdf_safe(docx_path: str, output_dir: str = "temp") -> str | None:
    """Safe DOCX→PDF conversion with cross-platform fallback chain."""
    pdf_path = docx_path.replace(".docx", ".pdf")
    os.makedirs(output_dir, exist_ok=True)

    try:
        from docx2pdf import convert
        convert(docx_path, pdf_path)
        if os.path.exists(pdf_path):
            logger.info(f"PDF via docx2pdf: {pdf_path}")
            return pdf_path
    except Exception as e:
        logger.debug(f"docx2pdf unavailable: {e}")

    try:
        import subprocess
        subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "pdf",
             docx_path, "--outdir", output_dir],
            check=True, timeout=60, capture_output=True,
        )
        if os.path.exists(pdf_path):
            logger.info(f"PDF via LibreOffice: {pdf_path}")
            return pdf_path
    except Exception as e:
        logger.debug(f"LibreOffice unavailable: {e}")

    logger.warning(f"PDF conversion failed for {docx_path}")
    return None
