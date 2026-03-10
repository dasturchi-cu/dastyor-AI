import os
from docx import Document
from docx.shared import Pt, Cm, RGBColor, Mm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ─────────────────────────────────────────────────────────────────────────────
# MULTILINGUAL LABELS
# ─────────────────────────────────────────────────────────────────────────────
_OBY_LBL = {
    "uz_lat": {
        "title":     "MA'LUMOTNOMA",
        "name_lbl":  "F.I.SH.",
        "bdate":     "Tug'ilgan yili, kuni va oyi",
        "bplace":    "Tug'ilgan joyi",
        "nation":    "Millati",
        "party":     "Partiyaviyligi",
        "edu":       "Ma'lumoti",
        "grad":      "Qaysi oliy (o'rta) maktabni tamomlagan",
        "spec":      "Mutaxassisligi",
        "degree":    "Ilmiy darajasi",
        "stitle":    "Ilmiy unvoni",
        "langs":     "Qaysi chet tillarini biladi",
        "military":  "Harbiy yoki maxsus unvoni",
        "awards":    "Davlat mukofotlari",
        "deputy":    "Deputatlik statusi",
        "exp_title": "MEHNAT FAOLIYATI",
        "exp_col1":  "Yillar",
        "exp_col2":  "Ish joyi va lavozimi",
        "rel_suffix":"YAQIN QARINDOSHLARI HAQIDA MA'LUMOT",
        "rel_c1":    "Qarindoshligi",
        "rel_c2":    "F.I.SH.",
        "rel_c3":    "Tug'ilgan yili va joyi",
        "rel_c4":    "Ish joyi va lavozimi",
        "rel_c5":    "Yashash manzili",
        "phone":     "Telefon raqami",
        "addr":      "Yashash manzili",
        "photo":     "4x6",
        "empty":     "—",
    },
    "uz_cyr": {
        "title":     "МАЪЛУМОТНОМА",
        "name_lbl":  "Ф.И.Ш.",
        "bdate":     "Туғилган йили, куни ва ойи",
        "bplace":    "Туғилган жойи",
        "nation":    "Миллати",
        "party":     "Партиявийлиги",
        "edu":       "Маълумоти",
        "grad":      "Қайси олий мактабни тамомлаган",
        "spec":      "Мутахассислиги",
        "degree":    "Илмий даражаси",
        "stitle":    "Илмий унвони",
        "langs":     "Қайси чет тилларини билади",
        "military":  "Ҳарбий ёки махсус унвони",
        "awards":    "Давлат мукофотлари",
        "deputy":    "Депутатлик статуси",
        "exp_title": "МЕҲНАТ ФАОЛИЯТИ",
        "exp_col1":  "Йиллар",
        "exp_col2":  "Иш жойи ва лавозими",
        "rel_suffix":"ЯҚИН ҚАРИНДОШЛАРИ ҲАҚИДА МАЪЛУМОТ",
        "rel_c1":    "Қариндошлиги",
        "rel_c2":    "Ф.И.Ш.",
        "rel_c3":    "Туғилган йили ва жойи",
        "rel_c4":    "Иш жойи ва лавозими",
        "rel_c5":    "Яшаш манзили",
        "phone":     "Телефон рақами",
        "addr":      "Яшаш манзили",
        "photo":     "4x6",
        "empty":     "—",
    },
    "en": {
        "title":     "CURRICULUM VITAE",
        "name_lbl":  "Full Name",
        "bdate":     "Date of Birth",
        "bplace":    "Place of Birth",
        "nation":    "Nationality",
        "party":     "Party Membership",
        "edu":       "Education",
        "grad":      "University Graduated From",
        "spec":      "Specialty",
        "degree":    "Academic Degree",
        "stitle":    "Academic Title",
        "langs":     "Foreign Languages",
        "military":  "Military Rank",
        "awards":    "State Awards",
        "deputy":    "Deputy Status",
        "exp_title": "WORK EXPERIENCE",
        "exp_col1":  "Period",
        "exp_col2":  "Position & Workplace",
        "rel_suffix":"CLOSE RELATIVES INFORMATION",
        "rel_c1":    "Relationship",
        "rel_c2":    "Full Name",
        "rel_c3":    "Year & Place of Birth",
        "rel_c4":    "Workplace & Position",
        "rel_c5":    "Home Address",
        "phone":     "Phone Number",
        "addr":      "Home Address",
        "photo":     "4x6",
        "empty":     "—",
    },
    "ru": {
        "title":     "ОБЪЕКТИВКА",
        "name_lbl":  "Ф.И.О.",
        "bdate":     "Год, число и месяц рождения",
        "bplace":    "Место рождения",
        "nation":    "Национальность",
        "party":     "Партийность",
        "edu":       "Образование",
        "grad":      "Какое учебное заведение окончил(а)",
        "spec":      "Специальность",
        "degree":    "Учёная степень",
        "stitle":    "Учёное звание",
        "langs":     "Какими иностранными языками владеет",
        "military":  "Воинское звание",
        "awards":    "Государственные награды",
        "deputy":    "Статус депутата",
        "exp_title": "ТРУДОВАЯ ДЕЯТЕЛЬНОСТЬ",
        "exp_col1":  "Годы",
        "exp_col2":  "Место работы и должность",
        "rel_suffix":"СВЕДЕНИЯ О БЛИЗКИХ РОДСТВЕННИКАХ",
        "rel_c1":    "Степень родства",
        "rel_c2":    "Ф.И.О.",
        "rel_c3":    "Год и место рождения",
        "rel_c4":    "Место работы и должность",
        "rel_c5":    "Место жительства",
        "phone":     "Номер телефона",
        "addr":      "Домашний адрес",
        "photo":     "4x6",
        "empty":     "—",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# DESIGN CONSTANTS (Simple B&W Classic Resume look)
# ─────────────────────────────────────────────────────────────────────────────
NAVY_CLR       = RGBColor(0x00, 0x00, 0x00)  # #000000 
NAVY_HEX       = "000000"
LIGHT_BLUE_HEX = "FFFFFF"
STRIPE_HEX     = "FFFFFF"
BORDER_HEX     = "000000"
LABEL_CLR      = RGBColor(0x00, 0x00, 0x00)  # #000000
DARK_TEXT      = RGBColor(0x1F, 0x1F, 0x1F)  # #1F1F1F (Oddiy to'q kulrang)

FONT_BODY = "Times New Roman"

def _set_margins(doc: Document) -> None:
    # A4 dimensions are 210mm x 297mm
    # CSS: padding: 18mm 16mm 20mm 20mm (top right bottom left) -> Top 18, Right 16, Bottom 20, Left 20
    for section in doc.sections:
        section.page_width = Mm(210)
        section.page_height = Mm(297)
        section.top_margin = Cm(2.0)
        section.right_margin = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(2.0)

def _get_page_width_emu(doc: Document) -> int:
    sec = doc.sections[0]
    return sec.page_width - sec.left_margin - sec.right_margin

# === XML Manipulations ===
def _cell_shading(cell, fill_hex: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex.lstrip("#"))
    tc_pr.append(shd)

def _remove_table_borders(table) -> None:
    tbl = table._tbl
    tblPr = tbl.find(qn("w:tblPr"))
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        tbl.insert(0, tblPr)
    tblBorders = OxmlElement("w:tblBorders")
    for side in ("top","left","bottom","right","insideH","insideV"):
        b = OxmlElement(f"w:{side}")
        b.set(qn("w:val"), "none")
        b.set(qn("w:sz"), "0")
        b.set(qn("w:space"), "0")
        b.set(qn("w:color"), "auto")
        tblBorders.append(b)
    tblPr.append(tblBorders)

def _set_cell_borders(cell, color_hex: str = BORDER_HEX, sz_val: str = "4", top=True, bottom=True, left=True, right=True) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_borders = tc_pr.find(qn("w:tcBorders"))
    if tc_borders is None:
        tc_borders = OxmlElement("w:tcBorders")
        tc_pr.append(tc_borders)
    
    borders = {"top": top, "bottom": bottom, "left": left, "right": right}
    for side, draw in borders.items():
        if draw:
            b = OxmlElement(f"w:{side}")
            b.set(qn("w:val"), "single")
            b.set(qn("w:sz"), sz_val)
            b.set(qn("w:space"), "0")
            b.set(qn("w:color"), color_hex.lstrip("#"))
            tc_borders.append(b)

def _set_col_widths(table, page_width_emu: int, pcts: list) -> None:
    for col_idx, pct in enumerate(pcts):
        w = int(page_width_emu * pct / 100)
        for cell in table.columns[col_idx].cells:
            tc = cell._tc
            tcW = tc.get_or_add_tcPr().find(qn("w:tcW"))
            if tcW is None:
                tcW = OxmlElement("w:tcW")
                tc.get_or_add_tcPr().append(tcW)
            tcW.set(qn("w:w"), str(w))
            tcW.set(qn("w:type"), "dxa")

def _para_spacing(para, before_pt=0, after_pt=0, line_rule=None):
    pPr = para._p.get_or_add_pPr()
    spacing = OxmlElement("w:spacing")
    spacing.set(qn("w:before"), str(int(before_pt * 20)))
    spacing.set(qn("w:after"),  str(int(after_pt  * 20)))
    if line_rule:
        spacing.set(qn("w:line"), str(int(line_rule * 240)))
    else:
        spacing.set(qn("w:line"), str(int(1.15 * 240)))
    spacing.set(qn("w:lineRule"), "auto")
    pPr.append(spacing)

def _run(para, text: str, bold=False, italic=False, size_pt: float=10.5, color: RGBColor=None, spacing_pt=None):
    r = para.add_run(text)
    r.bold = bold
    r.italic = italic
    r.font.name = FONT_BODY
    r.font.size = Pt(size_pt)
    if color:
        r.font.color.rgb = color
    if spacing_pt:
        rPr = r._r.get_or_add_rPr()
        spc = OxmlElement("w:spacing")
        spc.set(qn("w:val"), str(int(spacing_pt * 20)))
        rPr.append(spc)
    return r

def _add_hr(doc: Document, color_hex: str = NAVY_HEX, space_before=0, space_after=4):
    p = doc.add_paragraph()
    _para_spacing(p, before_pt=space_before, after_pt=space_after)
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")  # 0.75pt
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), color_hex.lstrip("#"))
    pBdr.append(bottom)
    p._p.get_or_add_pPr().append(pBdr)


def generate_obyektivka_docx(user_data: dict, photo_path: str, output_filepath: str):
    """
    Word hujjatini noldan, pixel-perfect ko'rinishda yaratadigan funktsiya.
    Dizayn A4 format, aniq margin va style parametrlari bilan yozilgan.
    Ko'p tilli: uz_lat | uz_cyr | en | ru
    """
    # ── Language setup ─────────────────────────────────────────────────
    lang = user_data.get('lang', 'uz_lat') or 'uz_lat'
    lb = _OBY_LBL.get(lang, _OBY_LBL['uz_lat'])

    doc = Document()
    _set_margins(doc)
    
    # Base Document Style Reset
    style = doc.styles["Normal"]
    style.font.name = FONT_BODY
    style.font.size = Pt(10.5)
    style.paragraph_format.space_before = Pt(0)
    style.paragraph_format.space_after = Pt(0)
    style.paragraph_format.line_spacing = 1.15
    
    pw = _get_page_width_emu(doc)

    # 1. Document Title
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _para_spacing(title_p, before_pt=16, after_pt=24)
    _run(title_p, lb['title'], bold=True, size_pt=20.0, color=RGBColor(0,0,0), spacing_pt=4)
    
    
    # 3. Header Table (Name & Photo)
    hdr_tbl = doc.add_table(rows=1, cols=2)
    _remove_table_borders(hdr_tbl)
    hdr_tbl.autofit = False
    _set_col_widths(hdr_tbl, pw, [72, 28])
    
    cell_name = hdr_tbl.cell(0, 0)
    _cell_shading(cell_name, "FFFFFF")

    np_lbl = cell_name.paragraphs[0]
    _para_spacing(np_lbl, before_pt=6, after_pt=2)
    np_lbl.paragraph_format.left_indent = Cm(0.3)
    _run(np_lbl, lb['name_lbl'], bold=False, size_pt=10.0, color=RGBColor(0x55, 0x55, 0x55), spacing_pt=1.0)
    
    np_val = cell_name.add_paragraph()
    _para_spacing(np_val, before_pt=2, after_pt=6, line_rule=1.1)
    np_val.paragraph_format.left_indent = Cm(0.3)
    _run(np_val, user_data.get('fullname', '').upper(), bold=True, size_pt=17.0, color=RGBColor(0,0,0), spacing_pt=0.5)

    cell_photo = hdr_tbl.cell(0, 1)
    _cell_shading(cell_photo, "FFFFFF") # It's white in original, or let's strictly check: it says col-img is transparent but photo-frame is inline-block border 2px #1a3a6b
    photo_p = cell_photo.paragraphs[0]
    photo_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    if photo_path and os.path.exists(photo_path):
        # Insert image with exact 30x40mm dimensions:
        r = photo_p.add_run()
        r.add_picture(photo_path, width=Mm(30), height=Mm(40))
        # Adding blue border around picture programmatically via Word is tricky, but doable via inline shape xml if strictly required.
    else:
        # Fallback to placeholder if missing
        _cell_shading(cell_photo, "FFFFFF")
        _para_spacing(photo_p, before_pt=40, after_pt=40)
        _run(photo_p, "4x6", size_pt=9.0, color=LABEL_CLR)

    doc.add_paragraph() # spacer

    # 4. Info Table
    info_rows = [
        (lb['bdate'],   user_data.get('birthdate', ''),      lb['bplace'],   user_data.get('birthplace', '')),
        (lb['nation'],  user_data.get('nation', ''),         lb['party'],    user_data.get('party', '')),
        (lb['edu'],     user_data.get('education', ''),      lb['grad'],     user_data.get('graduated', '')),
        (lb['spec'],    user_data.get('specialty', ''),      lb['degree'],   user_data.get('degree', '')),
        (lb['stitle'],  user_data.get('scientific_title',''),lb['langs'],    user_data.get('languages', '')),
        (lb['military'],user_data.get('military_rank','') or user_data.get('military', ''), lb['awards'], user_data.get('awards', '')),
        (lb['deputy'],  user_data.get('deputy', ''),         lb['phone'],    user_data.get('phone', '')),
    ]

    # Add extra row count for address (spans two columns)
    info_tbl = doc.add_table(rows=len(info_rows) + 1, cols=2)
    _remove_table_borders(info_tbl)
    info_tbl.autofit = False
    _set_col_widths(info_tbl, pw, [50, 50])

    for i, row_data in enumerate(info_rows):
        lbl1, val1, lbl2, val2 = row_data
        for j, (lbl, val) in enumerate([(lbl1, val1), (lbl2, val2)]):
            cell = info_tbl.cell(i, j)
            _cell_shading(cell, "FFFFFF")
            _set_cell_borders(cell, color_hex="E5E5E5", sz_val="4", top=False, bottom=True, left=False, right=False)

            pL = cell.paragraphs[0]
            _para_spacing(pL, before_pt=10, after_pt=2)
            pL.paragraph_format.left_indent = Cm(0.0)
            pL.paragraph_format.right_indent = Cm(0.4)
            _run(pL, lbl.upper(), bold=True, size_pt=10.0, color=RGBColor(0x37, 0x41, 0x51), spacing_pt=1.0)
            
            pV = cell.add_paragraph()
            _para_spacing(pV, before_pt=2, after_pt=10)
            pV.paragraph_format.left_indent = Cm(0.0)
            pV.paragraph_format.right_indent = Cm(0.4)
            _run(pV, val, bold=False, size_pt=12.0, color=RGBColor(0,0,0))

    # Add Address row (colspan = 2)
    addr_row_idx = len(info_rows)
    addr_cell = info_tbl.cell(addr_row_idx, 0)
    addr_cell.merge(info_tbl.cell(addr_row_idx, 1))
    _cell_shading(addr_cell, "FFFFFF")
    _set_cell_borders(addr_cell, color_hex="E5E5E5", sz_val="4", top=False, bottom=True, left=False, right=False)
    
    pLa = addr_cell.paragraphs[0]
    _para_spacing(pLa, before_pt=10, after_pt=2)
    pLa.paragraph_format.left_indent = Cm(0.0)
    _run(pLa, lb['addr'].upper(), bold=True, size_pt=10.0, color=RGBColor(0x37, 0x41, 0x51), spacing_pt=1.0)
    
    pVa = addr_cell.add_paragraph()
    _para_spacing(pVa, before_pt=2, after_pt=10)
    pVa.paragraph_format.left_indent = Cm(0.0)
    _run(pVa, user_data.get('address', '') or user_data.get('addr', ''), bold=False, size_pt=12.0, color=RGBColor(0,0,0))

    doc.add_paragraph()

    # 5. Work Experience Section Header
    sp = doc.add_paragraph()
    sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _para_spacing(sp, before_pt=24, after_pt=16)

    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "12") # 1.5pt
    bottom.set(qn("w:space"), "6")
    bottom.set(qn("w:color"), "000000")
    pBdr.append(bottom)
    sp._p.get_or_add_pPr().append(pBdr)

    _run(sp, lb['exp_title'], bold=True, size_pt=14.0, color=RGBColor(0,0,0), spacing_pt=3.0)

    # Work Table
    works = user_data.get("work_experience", [])
    if works:
        wtbl = doc.add_table(rows=1+len(works), cols=2)
        _remove_table_borders(wtbl)
        _set_col_widths(wtbl, pw, [26, 74])
        # Header
        h_years = wtbl.cell(0, 0)
        h_pos = wtbl.cell(0, 1)
        for hcell, ht in [(h_years, lb['exp_col1']), (h_pos, lb['exp_col2'])]:
            _cell_shading(hcell, "FFFFFF")
            _set_cell_borders(hcell, color_hex=BORDER_HEX, sz_val="12", top=True, bottom=True, left=False, right=False)
            hp = hcell.paragraphs[0]
            hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _para_spacing(hp, before_pt=8, after_pt=8)
            _run(hp, ht, bold=True, size_pt=11.0, color=RGBColor(0, 0, 0), spacing_pt=0.5)

        for i, work in enumerate(works):
            y_cell = wtbl.cell(1+i, 0)
            p_cell = wtbl.cell(1+i, 1)
            for cell, val, bold in [(y_cell, work.get('year', ''), True), (p_cell, work.get('position', ''), False)]:
                _cell_shading(cell, "FFFFFF")
                _set_cell_borders(cell, color_hex="CCCCCC", sz_val="4", top=False, bottom=True, left=False, right=False)
                cp = cell.paragraphs[0]
                _para_spacing(cp, before_pt=9, after_pt=9)
                cp.paragraph_format.left_indent = Cm(0.0)
                cp.paragraph_format.right_indent = Cm(0.4)
                _run(cp, val, bold=bold, size_pt=11.5, color=RGBColor(0,0,0))
    else:
        ep = doc.add_paragraph()
        ep.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(ep, "—", italic=True, size_pt=9.5, color=LABEL_CLR)

    doc.add_paragraph()

    # 6. Relatives Section Header
    fname = (user_data.get('fullname', '') or '').split(" ")[0].upper()
    rel_title = lb['rel_suffix'] if lang == 'ru' else f"{fname} {lb['rel_suffix']}"

    rp = doc.add_paragraph()
    rp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _para_spacing(rp, before_pt=24, after_pt=16)

    pBdr_r = OxmlElement("w:pBdr")
    bottom_r = OxmlElement("w:bottom")
    bottom_r.set(qn("w:val"), "single")
    bottom_r.set(qn("w:sz"), "12") # 1.5pt
    bottom_r.set(qn("w:space"), "6")
    bottom_r.set(qn("w:color"), "000000")
    pBdr_r.append(bottom_r)
    rp._p.get_or_add_pPr().append(pBdr_r)

    _run(rp, rel_title, bold=True, size_pt=14.0, color=RGBColor(0,0,0), spacing_pt=3.0)

    # Relatives Table
    rels = user_data.get("relatives", [])
    if rels:
        rtbl = doc.add_table(rows=1+len(rels), cols=5)
        _remove_table_borders(rtbl)
        _set_col_widths(rtbl, pw, [13, 20, 17, 28, 22])
        headers = [lb['rel_c1'], lb['rel_c2'], lb['rel_c3'], lb['rel_c4'], lb['rel_c5']]
        for j, h in enumerate(headers):
            hc = rtbl.cell(0, j)
            _cell_shading(hc, "EFEFEF")
            _set_cell_borders(hc, BORDER_HEX, "4")
            hcp = hc.paragraphs[0]
            hcp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _para_spacing(hcp, before_pt=6, after_pt=6)
            _run(hcp, h, bold=True, size_pt=10.0, color=RGBColor(0, 0, 0))
        
        for i, rel in enumerate(rels):
            bg = STRIPE_HEX if (i % 2 == 1) else "FFFFFF"
            vals = [rel.get('degree', ''), rel.get('fullname', ''), rel.get('birth_year_place', ''), rel.get('work_place', ''), rel.get('address', '')]
            for j, val in enumerate(vals):
                rc = rtbl.cell(1+i, j)
                _cell_shading(rc, bg)
                _set_cell_borders(rc, BORDER_HEX, "4")
                rcp = rc.paragraphs[0]
                rcp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                _para_spacing(rcp, before_pt=6, after_pt=6)
                _run(rcp, val, size_pt=10.0, color=RGBColor(0,0,0))
    else:
        ep = doc.add_paragraph()
        ep.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(ep, "—", italic=True, size_pt=9.5, color=LABEL_CLR)

    doc.save(output_filepath)
    return output_filepath

