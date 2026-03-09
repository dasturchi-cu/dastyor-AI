import os
from docx import Document
from docx.shared import Pt, Cm, RGBColor, Mm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ─────────────────────────────────────────────────────────────────────────────
# DESIGN CONSTANTS (Matched from CSS tokens)
# ─────────────────────────────────────────────────────────────────────────────
NAVY_CLR       = RGBColor(0x1A, 0x3A, 0x6B)  # #1a3a6b
NAVY_HEX       = "1A3A6B"
LIGHT_BLUE_HEX = "F0F4FB"
STRIPE_HEX     = "F8F9FC"
BORDER_HEX     = "C5D0E4"
LABEL_CLR      = RGBColor(0x4A, 0x5A, 0x80)  # #4a5a80
DARK_TEXT      = RGBColor(0x1A, 0x1A, 0x2E)  # #1a1a2e

FONT_BODY = "Times New Roman"

def _set_margins(doc: Document) -> None:
    # A4 dimensions are 210mm x 297mm
    # CSS: padding: 18mm 16mm 20mm 20mm (top right bottom left) -> Top 18, Right 16, Bottom 20, Left 20
    for section in doc.sections:
        section.page_width = Mm(210)
        section.page_height = Mm(297)
        section.top_margin = Mm(18)
        section.right_margin = Mm(16)
        section.bottom_margin = Mm(20)
        section.left_margin = Mm(20)

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
    """
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

    # 1. Top Accent Bar
    bar_tbl = doc.add_table(rows=1, cols=1)
    _remove_table_borders(bar_tbl)
    bar_cell = bar_tbl.cell(0, 0)
    _cell_shading(bar_cell, NAVY_HEX)
    bar_p = bar_cell.paragraphs[0]
    bar_p.paragraph_format.space_after = Pt(0)
    trHeight = OxmlElement("w:trHeight")
    trHeight.set(qn("w:val"), "80") # 4pt
    trHeight.set(qn("w:hRule"), "exact")
    bar_tbl.rows[0]._tr.get_or_add_trPr().append(trHeight)
    
    doc.add_paragraph()
    
    # 2. Document Title
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _para_spacing(title_p, before_pt=4, after_pt=6)
    _run(title_p, "MA'LUMOTNOMA", bold=True, size_pt=15.0, color=NAVY_CLR, spacing_pt=4)
    # Title line
    title_line_p = doc.add_paragraph()
    title_line_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _para_spacing(title_line_p, after_pt=12)
    # create a thin line (using fake text or border). Let's use a 60mm horizontal line image or border rule.
    # We will use paragraph border for now. Wait, HR takes full width. 
    # Let's just use text underscore hack or precise bottom border. Since it's centered 60mm width:
    
    
    # 3. Header Table (Name & Photo)
    hdr_tbl = doc.add_table(rows=1, cols=2)
    _remove_table_borders(hdr_tbl)
    hdr_tbl.autofit = False
    _set_col_widths(hdr_tbl, pw, [72, 28])
    
    cell_name = hdr_tbl.cell(0, 0)
    _cell_shading(cell_name, LIGHT_BLUE_HEX)
    _set_cell_borders(cell_name, BORDER_HEX, "4", top=True, bottom=True, right=True, left=False)
    _set_cell_borders(cell_name, NAVY_HEX, "24", left=True, top=False, bottom=False, right=False) # 3pt left line

    np_lbl = cell_name.paragraphs[0]
    _para_spacing(np_lbl, before_pt=6, after_pt=2)
    np_lbl.paragraph_format.left_indent = Cm(0.3)
    _run(np_lbl, "F.I.SH.", bold=False, size_pt=8.0, color=LABEL_CLR, spacing_pt=1.5)
    
    np_val = cell_name.add_paragraph()
    _para_spacing(np_val, before_pt=2, after_pt=6, line_rule=1.1)
    np_val.paragraph_format.left_indent = Cm(0.3)
    _run(np_val, user_data.get('fullname', '').upper(), bold=True, size_pt=14.0, color=DARK_TEXT, spacing_pt=0.5)

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
        _cell_shading(cell_photo, LIGHT_BLUE_HEX)
        _para_spacing(photo_p, before_pt=40, after_pt=40)
        _run(photo_p, "4x6", size_pt=9.0, color=LABEL_CLR)
        _set_cell_borders(cell_photo, NAVY_HEX, "12")

    doc.add_paragraph() # spacer

    # 4. Info Table
    info_rows = [
        ("Tug'ilgan yili, kuni va oyi", user_data.get('birthdate', ''), "Tug'ilgan joyi", user_data.get('birthplace', '')),
        ("Millati", user_data.get('nation', ''), "Partiyaviyligi", user_data.get('party', '')),
        ("Ma'lumoti", user_data.get('education', ''), "Tamomlagan", user_data.get('graduated', '')),
        ("Mutaxassisligi", user_data.get('specialty', ''), "Ilmiy darajasi", user_data.get('degree', '')),
        ("Ilmiy unvoni", user_data.get('scientific_title', ''), "Tillar", user_data.get('languages', '')),
        ("Mukofotlar", user_data.get('awards', ''), "Deputatlik statusi", user_data.get('deputy', '')),
    ]

    info_tbl = doc.add_table(rows=len(info_rows), cols=2)
    _remove_table_borders(info_tbl)
    info_tbl.autofit = False
    _set_col_widths(info_tbl, pw, [50, 50])

    for i, row_data in enumerate(info_rows):
        lbl1, val1, lbl2, val2 = row_data
        bg_hex = STRIPE_HEX if (i % 2 == 1) else "FFFFFF"

        for j, (lbl, val) in enumerate([(lbl1, val1), (lbl2, val2)]):
            cell = info_tbl.cell(i, j)
            _cell_shading(cell, bg_hex)
            _set_cell_borders(cell, BORDER_HEX, "4")
            
            pL = cell.paragraphs[0]
            _para_spacing(pL, before_pt=4, after_pt=1)
            pL.paragraph_format.left_indent = Cm(0.2)
            pL.paragraph_format.right_indent = Cm(0.2)
            _run(pL, lbl.upper(), bold=True, size_pt=8.5, color=LABEL_CLR, spacing_pt=0.3)
            
            pV = cell.add_paragraph()
            _para_spacing(pV, before_pt=1, after_pt=4)
            pV.paragraph_format.left_indent = Cm(0.2)
            pV.paragraph_format.right_indent = Cm(0.2)
            _run(pV, val, bold=False, size_pt=10.5, color=DARK_TEXT)

    doc.add_paragraph()

    # 5. Work Experience Section Header
    sect_tbl = doc.add_table(rows=1, cols=1)
    _remove_table_borders(sect_tbl)
    sect_cell = sect_tbl.cell(0, 0)
    _cell_shading(sect_cell, LIGHT_BLUE_HEX)
    _set_cell_borders(sect_cell, NAVY_HEX, "12", top=True, bottom=False, left=False, right=False) # Top 2px Navy
    _set_cell_borders(sect_cell, BORDER_HEX, "4", top=False, bottom=True, left=False, right=False) # Bottom thin
    sp = sect_cell.paragraphs[0]
    sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _para_spacing(sp, before_pt=4, after_pt=4)
    _run(sp, "MEHNAT FAOLIYATI", bold=True, size_pt=10.5, color=NAVY_CLR, spacing_pt=2)
    
    doc.add_paragraph()

    # Work Table
    works = user_data.get("work_experience", [])
    if works:
        wtbl = doc.add_table(rows=1+len(works), cols=2)
        _remove_table_borders(wtbl)
        _set_col_widths(wtbl, pw, [26, 74])
        # Header
        h_years = wtbl.cell(0, 0)
        h_pos = wtbl.cell(0, 1)
        for hcell, ht in [(h_years, "Yillar"), (h_pos, "Ish joyi va lavozimi")]:
            _cell_shading(hcell, NAVY_HEX)
            _set_cell_borders(hcell, NAVY_HEX, "4")
            hp = hcell.paragraphs[0]
            hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _para_spacing(hp, before_pt=4, after_pt=4)
            _run(hp, ht, bold=True, size_pt=9.5, color=RGBColor(255, 255, 255), spacing_pt=0.5)

        for i, work in enumerate(works):
            bg = STRIPE_HEX if (i % 2 == 1) else "FFFFFF"
            y_cell = wtbl.cell(1+i, 0)
            p_cell = wtbl.cell(1+i, 1)
            for cell, val, bold in [(y_cell, work.get('year', ''), True), (p_cell, work.get('position', ''), False)]:
                _cell_shading(cell, bg)
                _set_cell_borders(cell, BORDER_HEX, "4")
                cp = cell.paragraphs[0]
                _para_spacing(cp, before_pt=5, after_pt=5)
                cp.paragraph_format.left_indent = Cm(0.2)
                _run(cp, val, bold=bold, size_pt=10.0, color=(NAVY_CLR if bold else DARK_TEXT))
    else:
        ep = doc.add_paragraph()
        ep.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(ep, "—", italic=True, size_pt=9.5, color=LABEL_CLR)

    doc.add_paragraph()

    # 6. Relatives Section Header
    fname = (user_data.get('fullname', '')).split(" ")[0].upper()
    sect_rel = doc.add_table(rows=1, cols=1)
    _remove_table_borders(sect_rel)
    r_cell = sect_rel.cell(0, 0)
    _cell_shading(r_cell, LIGHT_BLUE_HEX)
    _set_cell_borders(r_cell, NAVY_HEX, "12", top=True, bottom=False, left=False, right=False)
    _set_cell_borders(r_cell, BORDER_HEX, "4", top=False, bottom=True, left=False, right=False)
    rp = r_cell.paragraphs[0]
    rp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _para_spacing(rp, before_pt=4, after_pt=4)
    _run(rp, f"{fname} YAQIN QARINDOSHLARI HAQIDA MA'LUMOT", bold=True, size_pt=10.5, color=NAVY_CLR, spacing_pt=2)

    doc.add_paragraph()

    # Relatives Table
    rels = user_data.get("relatives", [])
    if rels:
        rtbl = doc.add_table(rows=1+len(rels), cols=5)
        _remove_table_borders(rtbl)
        _set_col_widths(rtbl, pw, [13, 20, 17, 28, 22])
        headers = ["Qarindoshligi", "F.I.SH.", "Tug'ilgan yili va joyi", "Ish joyi va lavozimi", "Yashash manzili"]
        for j, h in enumerate(headers):
            hc = rtbl.cell(0, j)
            _cell_shading(hc, NAVY_HEX)
            _set_cell_borders(hc, NAVY_HEX, "4")
            hcp = hc.paragraphs[0]
            hcp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _para_spacing(hcp, before_pt=4, after_pt=4)
            _run(hcp, h, bold=True, size_pt=8.5, color=RGBColor(255, 255, 255))
        
        for i, rel in enumerate(rels):
            bg = STRIPE_HEX if (i % 2 == 1) else "FFFFFF"
            vals = [rel.get('degree', ''), rel.get('fullname', ''), rel.get('birth_year_place', ''), rel.get('work_place', ''), rel.get('address', '')]
            for j, val in enumerate(vals):
                rc = rtbl.cell(1+i, j)
                _cell_shading(rc, bg)
                _set_cell_borders(rc, BORDER_HEX, "4")
                rcp = rc.paragraphs[0]
                rcp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                _para_spacing(rcp, before_pt=4, after_pt=4)
                _run(rcp, val, size_pt=9.0, color=DARK_TEXT)
    else:
        ep = doc.add_paragraph()
        ep.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(ep, "—", italic=True, size_pt=9.5, color=LABEL_CLR)

    doc.save(output_filepath)
    return output_filepath

