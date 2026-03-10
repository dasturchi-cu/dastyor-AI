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
        "name_lbl":  "F.I.SH.",
        "bdate":     "TUG'ILGAN YILI, KUNI VA OYI",
        "bplace":    "TUG'ILGAN JOYI",
        "nation":    "MILLATI",
        "party":     "PARTIYAVIYLIGI",
        "edu":       "MA'LUMOTI",
        "grad":      "TAMOMLAGAN",
        "spec":      "MUTAXASSISLIGI",
        "degree":    "ILMIY DARAJASI",
        "stitle":    "ILMIY UNVONI",
        "langs":     "CHET TILLARNI BILISHI",
        "military":  "HARBIY/MAXSUS UNVONI",
        "awards":    "DAVLAT MUKOFOTLARI",
        "deputy":    "DEPUTATLIK STATUSI",
        "phone":     "TELEFON",
        "addr":      "YASHASH MANZILI",
        "exp_title": "MEHNAT  FAOLIYATI",
        "exp_col1":  "YILLARI",
        "exp_col2":  "ISH JOYI VA EGALLAGAN LAVOZIMLARI",
        "rel_suffix":"YAQIN QARINDOSHLARI HAQIDA MA'LUMOT",
        "rel_c1":    "QARINDOSHLIGI",
        "rel_c2":    "F.I.SH.",
        "rel_c3":    "TUG'ILGAN YILI VA JOYI",
        "rel_c4":    "ISH JOYI VA LAVOZIMI",
        "rel_c5":    "YASHASH MANZILI",
        "photo":     "3x4",
        "empty":     "—",
    },
    "uz_cyr": {
        "name_lbl":  "Ф.И.Ш.",
        "bdate":     "ТУҒИЛГАН ЙИЛИ, КУНИ ВА ОЙИ",
        "bplace":    "ТУҒИЛГАН ЖОЙИ",
        "nation":    "МИЛЛАТИ",
        "party":     "ПАРТИЯВИЙЛИГИ",
        "edu":       "МАЪЛУМОТИ",
        "grad":      "ТАМОМЛАГАН",
        "spec":      "МУТАХАССИСЛИГИ",
        "degree":    "ИЛМИЙ ДАРАЖАСИ",
        "stitle":    "ИЛМИЙ УНВОНИ",
        "langs":     "ЧЕТ ТИЛЛАРНИ БИЛИШИ",
        "military":  "ҲАРБИЙ/МАХСУС УНВОНИ",
        "awards":    "ДАВЛАТ МУКОФОТЛАРИ",
        "deputy":    "ДЕПУТАТЛИК СТАТУСИ",
        "phone":     "ТЕЛЕФОН",
        "addr":      "ЯШАШ МАНЗИЛИ",
        "exp_title": "МЕҲНАТ  ФАОЛИЯТИ",
        "exp_col1":  "ЙИЛЛАРИ",
        "exp_col2":  "ИШ ЖОЙИ ВА ЭГАЛЛАГАН ЛАВОЗИМЛАРИ",
        "rel_suffix":"ЯҚИН ҚАРИНДОШЛАРИ ҲАҚИДА МАЪЛУМОТ",
        "rel_c1":    "ҚАРИНДОШЛИГИ",
        "rel_c2":    "Ф.И.Ш.",
        "rel_c3":    "ТУҒИЛГАН ЙИЛИ ВА ЖОЙИ",
        "rel_c4":    "ИШ ЖОЙИ ВА ЛАВОЗИМИ",
        "rel_c5":    "ЯШАШ МАНЗИЛИ",
        "photo":     "3x4",
        "empty":     "—",
    },
    "en": {
        "name_lbl":  "Full Name",
        "bdate":     "DATE OF BIRTH",
        "bplace":    "PLACE OF BIRTH",
        "nation":    "NATIONALITY",
        "party":     "PARTY MEMBERSHIP",
        "edu":       "EDUCATION",
        "grad":      "GRADUATED FROM",
        "spec":      "SPECIALTY",
        "degree":    "ACADEMIC DEGREE",
        "stitle":    "ACADEMIC TITLE",
        "langs":     "FOREIGN LANGUAGES",
        "military":  "MILITARY RANK",
        "awards":    "STATE AWARDS",
        "deputy":    "DEPUTY STATUS",
        "phone":     "PHONE",
        "addr":      "HOME ADDRESS",
        "exp_title": "WORK  EXPERIENCE",
        "exp_col1":  "PERIOD",
        "exp_col2":  "POSITION & WORKPLACE",
        "rel_suffix":"CLOSE RELATIVES INFORMATION",
        "rel_c1":    "RELATIONSHIP",
        "rel_c2":    "FULL NAME",
        "rel_c3":    "YEAR & PLACE OF BIRTH",
        "rel_c4":    "WORKPLACE & POSITION",
        "rel_c5":    "HOME ADDRESS",
        "photo":     "3x4",
        "empty":     "—",
    },
    "ru": {
        "name_lbl":  "Ф.И.О.",
        "bdate":     "ГОД, ЧИСЛО И МЕСЯЦ РОЖДЕНИЯ",
        "bplace":    "МЕСТО РОЖДЕНИЯ",
        "nation":    "НАЦИОНАЛЬНОСТЬ",
        "party":     "ПАРТИЙНОСТЬ",
        "edu":       "ОБРАЗОВАНИЕ",
        "grad":      "ОКОНЧИЛ(А)",
        "spec":      "СПЕЦИАЛЬНОСТЬ",
        "degree":    "УЧЁНАЯ СТЕПЕНЬ",
        "stitle":    "УЧЁНОЕ ЗВАНИЕ",
        "langs":     "ИНОСТРАННЫЕ ЯЗЫКИ",
        "military":  "ВОИНСКОЕ ЗВАНИЕ",
        "awards":    "ГОСУДАРСТВЕННЫЕ НАГРАДЫ",
        "deputy":    "СТАТУС ДЕПУТАТА",
        "phone":     "ТЕЛЕФОН",
        "addr":      "ДОМАШНИЙ АДРЕС",
        "exp_title": "ТРУДОВАЯ  ДЕЯТЕЛЬНОСТЬ",
        "exp_col1":  "ГОДЫ",
        "exp_col2":  "МЕСТО РАБОТЫ И ДОЛЖНОСТЬ",
        "rel_suffix":"СВЕДЕНИЯ О БЛИЗКИХ РОДСТВЕННИКАХ",
        "rel_c1":    "СТЕПЕНЬ РОДСТВА",
        "rel_c2":    "Ф.И.О.",
        "rel_c3":    "ГОД И МЕСТО РОЖДЕНИЯ",
        "rel_c4":    "МЕСТО РАБОТЫ И ДОЛЖНОСТЬ",
        "rel_c5":    "МЕСТО ЖИТЕЛЬСТВА",
        "photo":     "3x4",
        "empty":     "—",
    },
}

FONT       = "Times New Roman"
BLACK      = RGBColor(0x00, 0x00, 0x00)
DARK       = RGBColor(0x1A, 0x1A, 0x1A)
LABEL_CLR  = RGBColor(0x22, 0x22, 0x22)
MUTED      = RGBColor(0x88, 0x88, 0x88)
WHITE_HEX  = "FFFFFF"
GREY_HEX   = "F2F2F2"
LINE_CLR   = "AAAAAA"   # ingichka separator
BOLD_LINE  = "111111"   # bo'lim sarlavhasi ostidagi qalin chiziq
DASH_CLR   = "BBBBBB"   # foto punktir

# ─────────────────────────────────────────────────────────────────────────────
# XML HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _set_margins(doc):
    for s in doc.sections:
        s.page_width    = Mm(210)
        s.page_height   = Mm(297)
        s.top_margin    = Cm(2.2)
        s.bottom_margin = Cm(2.0)
        s.left_margin   = Cm(2.5)
        s.right_margin  = Cm(2.2)

def _pw(doc):
    s = doc.sections[0]
    return s.page_width - s.left_margin - s.right_margin

def _no_borders(table):
    tbl   = table._tbl
    tblPr = tbl.find(qn("w:tblPr")) or OxmlElement("w:tblPr")
    if tbl.find(qn("w:tblPr")) is None:
        tbl.insert(0, tblPr)
    tb = OxmlElement("w:tblBorders")
    for side in ("top","left","bottom","right","insideH","insideV"):
        b = OxmlElement(f"w:{side}")
        b.set(qn("w:val"),"none"); b.set(qn("w:sz"),"0")
        b.set(qn("w:space"),"0"); b.set(qn("w:color"),"auto")
        tb.append(b)
    tblPr.append(tb)

def _col_w(table, pw, pcts):
    for ci, pct in enumerate(pcts):
        w = int(pw * pct / 100)
        for cell in table.columns[ci].cells:
            tcPr = cell._tc.get_or_add_tcPr()
            tcW  = tcPr.find(qn("w:tcW")) or OxmlElement("w:tcW")
            if tcPr.find(qn("w:tcW")) is None:
                tcPr.append(tcW)
            tcW.set(qn("w:w"), str(w)); tcW.set(qn("w:type"), "dxa")

def _shading(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd  = OxmlElement("w:shd")
    shd.set(qn("w:val"),"clear"); shd.set(qn("w:color"),"auto")
    shd.set(qn("w:fill"), hex_fill.lstrip("#"))
    tcPr.append(shd)

def _cell_pad(cell, top=80, bottom=80, left=0, right=0):
    tcPr  = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for s, v in [("top",top),("bottom",bottom),("left",left),("right",right)]:
        m = OxmlElement(f"w:{s}")
        m.set(qn("w:w"), str(v)); m.set(qn("w:type"), "dxa")
        tcMar.append(m)
    tcPr.append(tcMar)

def _cell_bottom_border(cell, color=LINE_CLR, sz="4"):
    tcPr = cell._tc.get_or_add_tcPr()
    tb   = OxmlElement("w:tcBorders")
    for s in ("top","left","right"):
        b = OxmlElement(f"w:{s}"); b.set(qn("w:val"),"none"); tb.append(b)
    bot = OxmlElement("w:bottom")
    bot.set(qn("w:val"),"single"); bot.set(qn("w:sz"),sz)
    bot.set(qn("w:space"),"0");    bot.set(qn("w:color"),color.lstrip("#"))
    tb.append(bot); tcPr.append(tb)

def _cell_top_border(cell, color=BOLD_LINE, sz="8"):
    tcPr = cell._tc.get_or_add_tcPr()
    tb   = OxmlElement("w:tcBorders")
    for s in ("bottom","left","right"):
        b = OxmlElement(f"w:{s}"); b.set(qn("w:val"),"none"); tb.append(b)
    top = OxmlElement("w:top")
    top.set(qn("w:val"),"single"); top.set(qn("w:sz"),sz)
    top.set(qn("w:space"),"0");    top.set(qn("w:color"),color.lstrip("#"))
    tb.append(top); tcPr.append(tb)

def _cell_all_borders(cell, color=LINE_CLR, sz="4"):
    tcPr = cell._tc.get_or_add_tcPr()
    tb   = OxmlElement("w:tcBorders")
    for s in ("top","left","bottom","right"):
        b = OxmlElement(f"w:{s}")
        b.set(qn("w:val"),"single"); b.set(qn("w:sz"),sz)
        b.set(qn("w:space"),"0");    b.set(qn("w:color"),color.lstrip("#"))
        tb.append(b)
    tcPr.append(tb)

def _cell_dashed_all(cell, color=DASH_CLR, sz="6"):
    tcPr = cell._tc.get_or_add_tcPr()
    tb   = OxmlElement("w:tcBorders")
    for s in ("top","left","bottom","right"):
        b = OxmlElement(f"w:{s}")
        b.set(qn("w:val"),"dashed"); b.set(qn("w:sz"),sz)
        b.set(qn("w:space"),"0");    b.set(qn("w:color"),color.lstrip("#"))
        tb.append(b)
    tcPr.append(tb)

def _spc(para, before=0, after=0, line=1.15):
    pPr = para._p.get_or_add_pPr()
    sp  = OxmlElement("w:spacing")
    sp.set(qn("w:before"), str(int(before*20)))
    sp.set(qn("w:after"),  str(int(after*20)))
    sp.set(qn("w:line"),   str(int(line*240)))
    sp.set(qn("w:lineRule"),"auto")
    pPr.append(sp)

def _run(para, text, bold=False, italic=False, size=11.0,
         color=None, lspc=None):
    r = para.add_run(text)
    r.bold = bold; r.italic = italic
    r.font.name = FONT; r.font.size = Pt(size)
    if color: r.font.color.rgb = color
    if lspc is not None:
        rPr = r._r.get_or_add_rPr()
        sc  = OxmlElement("w:spacing")
        sc.set(qn("w:val"), str(int(lspc*20)))
        rPr.append(sc)

def _sect_title_para(doc, text):
    """Bo'lim sarlavhasi: katta harf + letter-spacing + ostida qalin chiziq."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    _spc(p, before=0, after=6, line=1.0)
    # bottom border
    pPr  = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bot  = OxmlElement("w:bottom")
    bot.set(qn("w:val"),"single"); bot.set(qn("w:sz"),"10")
    bot.set(qn("w:space"),"5");    bot.set(qn("w:color"),BOLD_LINE)
    pBdr.append(bot); pPr.append(pBdr)
    _run(p, text, bold=True, size=12.0, color=BLACK, lspc=2.5)
    return p

def _info_row(doc, pw, label, value):
    """
    Rasmdagi info qatori: to'liq kenglik jadval (1 ustun),
    label kichik harf yuqorida, value pastida, ost chiziq.
    """
    t = doc.add_table(rows=1, cols=1)
    _no_borders(t); t.autofit = False
    _col_w(t, pw, [100])
    cell = t.cell(0, 0)
    _shading(cell, WHITE_HEX)
    _cell_bottom_border(cell, color=LINE_CLR, sz="4")
    _cell_pad(cell, top=60, bottom=60, left=0, right=0)

    p_lbl = cell.paragraphs[0]
    _spc(p_lbl, before=0, after=1, line=1.0)
    _run(p_lbl, label, bold=False, size=7.5, color=LABEL_CLR, lspc=1.5)

    p_val = cell.add_paragraph()
    _spc(p_val, before=0, after=0, line=1.1)
    _run(p_val, value or "", bold=False, size=11.0, color=DARK)

def _info_row_2col(doc, pw, lbl1, val1, lbl2, val2):
    """
    Ikki ustunli info qatori (rasmdagi yon-yon juft qatorlar uchun).
    """
    t = doc.add_table(rows=1, cols=2)
    _no_borders(t); t.autofit = False
    _col_w(t, pw, [50, 50])

    for j, (lbl, val) in enumerate([(lbl1, val1), (lbl2, val2)]):
        cell = t.cell(0, j)
        _shading(cell, WHITE_HEX)
        _cell_bottom_border(cell, LINE_CLR, "4")
        _cell_pad(cell, top=60, bottom=60,
                  left=0, right=200 if j == 0 else 0)

        p_lbl = cell.paragraphs[0]
        _spc(p_lbl, before=0, after=1, line=1.0)
        _run(p_lbl, lbl, bold=False, size=7.5, color=LABEL_CLR, lspc=1.5)

        p_val = cell.add_paragraph()
        _spc(p_val, before=0, after=0, line=1.1)
        _run(p_val, val or "", bold=False, size=11.0, color=DARK)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_obyektivka_docx(user_data: dict, photo_path: str,
                              output_filepath: str) -> str:
    lang = user_data.get("lang","uz_lat") or "uz_lat"
    lb   = _OBY_LBL.get(lang, _OBY_LBL["uz_lat"])

    doc = Document()
    _set_margins(doc)
    ns = doc.styles["Normal"]
    ns.font.name = FONT; ns.font.size = Pt(11)
    ns.paragraph_format.space_before = Pt(0)
    ns.paragraph_format.space_after  = Pt(0)

    pw = _pw(doc)

    # ═══════════════════════════════════════════════════════
    # 1. HEADER: F.I.SH + ism (chap) | 3x4 foto (o'ng)
    # ═══════════════════════════════════════════════════════
    hdr = doc.add_table(rows=1, cols=2)
    _no_borders(hdr); hdr.autofit = False
    _col_w(hdr, pw, [68, 32])

    # Chap: name block
    nc = hdr.cell(0, 0)
    _shading(nc, WHITE_HEX)
    _cell_pad(nc, top=0, bottom=120, left=0, right=300)

    p_lbl = nc.paragraphs[0]
    _spc(p_lbl, before=0, after=4, line=1.0)
    _run(p_lbl, lb["name_lbl"], bold=False, size=8.0,
         color=LABEL_CLR, lspc=1.5)

    p_nm = nc.add_paragraph()
    _spc(p_nm, before=2, after=0, line=1.15)
    fullname = (user_data.get("fullname","") or "").upper()
    _run(p_nm, fullname, bold=True, size=15.0, color=BLACK)

    # O'ng: foto — punktir chegara, markazda
    pc = hdr.cell(0, 1)
    _shading(pc, WHITE_HEX)
    _cell_dashed_all(pc, DASH_CLR, "6")
    _cell_pad(pc, top=100, bottom=100, left=80, right=80)

    p_ph = pc.paragraphs[0]
    p_ph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _spc(p_ph, before=0, after=0, line=1.0)

    if photo_path and os.path.exists(photo_path):
        r = p_ph.add_run()
        r.add_picture(photo_path, width=Mm(25), height=Mm(33))
    else:
        _run(p_ph, lb["photo"], bold=False, size=9.0, color=MUTED)

    # Spacer
    sp = doc.add_paragraph(); _spc(sp, before=0, after=18)

    # ═══════════════════════════════════════════════════════
    # 2. INFO QATORLARI
    #    Rasmdagi tartib: har bir qator to'liq kenglik,
    #    label kichik yuqorida, qiymat pastida, ostida chiziq.
    #    Juft maydonlar yon-yon (2 ustun).
    # ═══════════════════════════════════════════════════════

    # Juft qatorlar (2 ustun)
    pairs = [
        (lb["bdate"],   user_data.get("birthdate","")   or user_data.get("bdate",""),
         lb["bplace"],  user_data.get("birthplace","")  or user_data.get("bplace","")),
        (lb["nation"],  user_data.get("nation",""),
         lb["party"],   user_data.get("party","")),
        (lb["edu"],     user_data.get("education","")   or user_data.get("edu",""),
         lb["grad"],    user_data.get("graduated","")   or user_data.get("grad","")),
        (lb["spec"],    user_data.get("specialty","")   or user_data.get("spec",""),
         lb["degree"],  user_data.get("degree","")),
        (lb["stitle"],  user_data.get("scientific_title","") or user_data.get("stitle",""),
         lb["langs"],   user_data.get("languages","")   or user_data.get("langs","")),
        (lb["military"],user_data.get("military_rank","") or user_data.get("military",""),
         lb["awards"],  user_data.get("awards","")),
        (lb["deputy"],  user_data.get("deputy",""),
         lb["phone"],   user_data.get("phone","")),
    ]

    for lbl1, val1, lbl2, val2 in pairs:
        _info_row_2col(doc, pw, lbl1, val1, lbl2, val2)

    # To'liq kenglik: manzil
    _info_row(doc, pw, lb["addr"],
              user_data.get("address","") or user_data.get("addr",""))

    # Spacer
    sp2 = doc.add_paragraph(); _spc(sp2, before=0, after=18)

    # ═══════════════════════════════════════════════════════
    # 3. MEHNAT FAOLIYATI
    # ═══════════════════════════════════════════════════════
    _sect_title_para(doc, lb["exp_title"])

    works = user_data.get("work_experience",[]) or []
    wtbl  = doc.add_table(rows=1 + max(1, len(works)), cols=2)
    _no_borders(wtbl); wtbl.autofit = False
    _col_w(wtbl, pw, [25, 75])

    # Header qator — kulrang fon, kichik label uslubi
    for j, ht in enumerate([lb["exp_col1"], lb["exp_col2"]]):
        hc = wtbl.cell(0, j)
        _shading(hc, GREY_HEX)
        _cell_top_border(hc, BOLD_LINE, "8")
        _cell_bottom_border(hc, BOLD_LINE, "8")
        _cell_pad(hc, top=80, bottom=80,
                  left=0 if j==0 else 120, right=0)
        hp = hc.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
        _spc(hp, before=0, after=0, line=1.0)
        _run(hp, ht, bold=False, size=8.0, color=LABEL_CLR, lspc=1.0)

    # Ma'lumot qatorlari
    for i, work in enumerate(works if works else [{"year":"","position":""}]):
        year = work.get("year","") or work.get("years","") or ""
        pos  = work.get("position","") or work.get("pos","") or ""
        for j, (cell, val) in enumerate([
            (wtbl.cell(1+i, 0), year),
            (wtbl.cell(1+i, 1), pos),
        ]):
            _shading(cell, WHITE_HEX)
            _cell_bottom_border(cell, LINE_CLR, "4")
            _cell_pad(cell, top=80, bottom=80,
                      left=0 if j==0 else 120, right=0)
            cp = cell.paragraphs[0]
            _spc(cp, before=0, after=0, line=1.15)
            _run(cp, val, bold=False, size=11.0, color=DARK)

    # Spacer
    sp3 = doc.add_paragraph(); _spc(sp3, before=0, after=18)

    # ═══════════════════════════════════════════════════════
    # 4. YAQIN QARINDOSHLARI
    # ═══════════════════════════════════════════════════════
    fname = (user_data.get("fullname","") or "").split()[0].upper() if user_data.get("fullname") else ""
    if lang == "ru":
        rel_title = lb["rel_suffix"]
    else:
        rel_title = f"{fname} {lb['rel_suffix']}" if fname else lb["rel_suffix"]

    _sect_title_para(doc, rel_title)

    rels = user_data.get("relatives",[]) or []
    rtbl = doc.add_table(rows=1 + max(1, len(rels)), cols=5)
    _no_borders(rtbl); rtbl.autofit = False
    _col_w(rtbl, pw, [13, 19, 18, 28, 22])

    # Header
    for j, h in enumerate([lb["rel_c1"],lb["rel_c2"],lb["rel_c3"],lb["rel_c4"],lb["rel_c5"]]):
        hc = rtbl.cell(0, j)
        _shading(hc, GREY_HEX)
        _cell_all_borders(hc, LINE_CLR, "4")
        _cell_pad(hc, top=80, bottom=80, left=80, right=80)
        hcp = hc.paragraphs[0]
        hcp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _spc(hcp, before=0, after=0, line=1.1)
        _run(hcp, h, bold=False, size=7.5, color=LABEL_CLR, lspc=0.5)

    # Data
    for i, rel in enumerate(rels if rels else [{}]):
        vals = [
            rel.get("degree","")          or rel.get("kin",""),
            rel.get("fullname","")         or rel.get("fish",""),
            rel.get("birth_year_place","") or rel.get("birth",""),
            rel.get("work_place","")       or rel.get("work",""),
            rel.get("address","")          or rel.get("addr",""),
        ]
        for j, val in enumerate(vals):
            rc = rtbl.cell(1+i, j)
            _shading(rc, WHITE_HEX)
            _cell_all_borders(rc, LINE_CLR, "4")
            _cell_pad(rc, top=70, bottom=70, left=80, right=80)
            rcp = rc.paragraphs[0]
            rcp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _spc(rcp, before=0, after=0, line=1.1)
            _run(rcp, val or "", size=10.0, color=DARK)

    doc.save(output_filepath)
    return output_filepath


# ─────────────────────────────────────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample = {
        "lang": "uz_lat",
        "fullname": "Familiya Ism Sharif",
        "birthdate": "",
        "birthplace": "",
        "nation": "",
        "party": "Dasds",
        "education": "",
        "graduated": "",
        "specialty": "",
        "degree": "",
        "scientific_title": "",
        "languages": "",
        "military": "",
        "awards": "",
        "deputy": "",
        "phone": "",
        "address": "",
        "work_experience": [
            {"year": "", "position": "dasds"},
        ],
        "relatives": [
            {"degree": "", "fullname": "Dasd",
             "birth_year_place": "", "work_place": "", "address": ""},
        ],
    }
    out = generate_obyektivka_docx(sample, "", "/home/claude/test_v4.docx")
    print(f"✓ Saved: {out}")
