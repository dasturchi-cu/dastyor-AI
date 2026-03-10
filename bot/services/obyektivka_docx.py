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
        "no_data":   "Ma'lumot yo'q",
    },
    "uz_cyr": {
        "title":     "МАЪЛУМОТНОМА",
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
        "no_data":   "Маълумот йўқ",
    },
    "en": {
        "title":     "CURRICULUM VITAE",
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
        "no_data":   "No data",
    },
    "ru": {
        "title":     "ОБЪЕКТИВКА",
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
        "no_data":   "Нет данных",
    },
}

FONT      = "Times New Roman"
BLACK     = RGBColor(0x00, 0x00, 0x00)
DARK      = RGBColor(0x1A, 0x1A, 0x1A)
LABEL_CLR = RGBColor(0x11, 0x11, 0x11)
MUTED     = RGBColor(0xAA, 0xAA, 0xAA)
ITALIC_C  = RGBColor(0x77, 0x77, 0x77)
NAVY_HEX  = "1A3A6B"
LINE_HEX  = "CCCCCC"
WHITE_HEX = "FFFFFF"
GREY_HEX  = "F5F5F5"


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
    tblPr = tbl.find(qn("w:tblPr"))
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
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
            old  = tcPr.find(qn("w:tcW"))
            if old is not None:
                tcPr.remove(old)
            tcW = OxmlElement("w:tcW")
            tcW.set(qn("w:w"), str(w))
            tcW.set(qn("w:type"), "dxa")
            tcPr.append(tcW)

def _shading(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd  = OxmlElement("w:shd")
    shd.set(qn("w:val"),"clear")
    shd.set(qn("w:color"),"auto")
    shd.set(qn("w:fill"), hex_fill.lstrip("#"))
    tcPr.append(shd)

def _cell_pad(cell, top=80, bottom=80, left=0, right=0):
    tcPr  = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for s, v in [("top",top),("bottom",bottom),("left",left),("right",right)]:
        m = OxmlElement(f"w:{s}")
        m.set(qn("w:w"), str(v))
        m.set(qn("w:type"), "dxa")
        tcMar.append(m)
    tcPr.append(tcMar)

def _cell_bottom_only(cell, color=LINE_HEX, sz="4"):
    """Faqat pastki chiziq."""
    tcPr = cell._tc.get_or_add_tcPr()
    tb   = OxmlElement("w:tcBorders")
    for s in ("top","left","right"):
        b = OxmlElement(f"w:{s}")
        b.set(qn("w:val"), "none")
        tb.append(b)
    bot = OxmlElement("w:bottom")
    bot.set(qn("w:val"),   "single")
    bot.set(qn("w:sz"),    sz)
    bot.set(qn("w:space"), "0")
    bot.set(qn("w:color"), color.lstrip("#"))
    tb.append(bot)
    tcPr.append(tb)

def _cell_no_borders(cell):
    """Hech qanday chegara yo'q."""
    tcPr = cell._tc.get_or_add_tcPr()
    tb   = OxmlElement("w:tcBorders")
    for s in ("top","left","bottom","right"):
        b = OxmlElement(f"w:{s}")
        b.set(qn("w:val"), "none")
        tb.append(b)
    tcPr.append(tb)

def _cell_all_borders(cell, color=LINE_HEX, sz="4"):
    tcPr = cell._tc.get_or_add_tcPr()
    tb   = OxmlElement("w:tcBorders")
    for s in ("top","left","bottom","right"):
        b = OxmlElement(f"w:{s}")
        b.set(qn("w:val"),   "single")
        b.set(qn("w:sz"),    sz)
        b.set(qn("w:space"), "0")
        b.set(qn("w:color"), color.lstrip("#"))
        tb.append(b)
    tcPr.append(tb)

def _cell_dashed_all(cell, color="BBBBBB", sz="6"):
    tcPr = cell._tc.get_or_add_tcPr()
    tb   = OxmlElement("w:tcBorders")
    for s in ("top","left","bottom","right"):
        b = OxmlElement(f"w:{s}")
        b.set(qn("w:val"),   "dashed")
        b.set(qn("w:sz"),    sz)
        b.set(qn("w:space"), "0")
        b.set(qn("w:color"), color.lstrip("#"))
        tb.append(b)
    tcPr.append(tb)

def _spc(para, before=0, after=0, line=1.15):
    pPr = para._p.get_or_add_pPr()
    sp  = OxmlElement("w:spacing")
    sp.set(qn("w:before"),   str(int(before * 20)))
    sp.set(qn("w:after"),    str(int(after  * 20)))
    sp.set(qn("w:line"),     str(int(line   * 240)))
    sp.set(qn("w:lineRule"), "auto")
    pPr.append(sp)

def _run(para, text, bold=False, italic=False,
         size=11.0, color=None, lspc=None):
    r = para.add_run(text)
    r.bold       = bold
    r.italic     = italic
    r.font.name  = FONT
    r.font.size  = Pt(size)
    if color:
        r.font.color.rgb = color
    if lspc is not None:
        rPr = r._r.get_or_add_rPr()
        sc  = OxmlElement("w:spacing")
        sc.set(qn("w:val"), str(int(lspc * 20)))
        rPr.append(sc)
    return r

def _vcenter(cell):
    tcPr   = cell._tc.get_or_add_tcPr()
    vAlign = OxmlElement("w:vAlign")
    vAlign.set(qn("w:val"), "center")
    tcPr.append(vAlign)

def _sect_title(doc, text):
    """
    Bo'lim sarlavhasi: qalin, katta harf, letter-spacing.
    Ostida NAVY ko'k ingichka chiziq (paragraph border).
    Rasmdagi bilan aynan bir xil.
    """
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    _spc(p, before=0, after=10, line=1.0)

    pPr  = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bot  = OxmlElement("w:bottom")
    bot.set(qn("w:val"),   "single")
    bot.set(qn("w:sz"),    "6")       # 0.75pt — ingichka
    bot.set(qn("w:space"), "6")
    bot.set(qn("w:color"), NAVY_HEX)
    pBdr.append(bot)
    pPr.append(pBdr)

    _run(p, text, bold=True, size=12.0, color=BLACK, lspc=2.5)
    return p


# ─────────────────────────────────────────────────────────────────────────────
# INFO QATOR KOMPONENTI
# Rasmda: label (8pt, kichik, yuqorida) + qiymat (11pt, pastida)
# Ikkala ustun birgalikda TO'LIQ kenglikka cho'zilgan bir chiziq bilan.
# ─────────────────────────────────────────────────────────────────────────────

def _info_block_2col(doc, pw, lbl1, val1, lbl2, val2):
    """
    Bir jadval qatori — 2 ustun.
    Pastki chiziq ikkala ustun qoshilib TO'LIQ kenglikda cho'ziladi.
    Label va qiymat orasida masofa yo'q (ketma-ket paragraflar).
    """
    t = doc.add_table(rows=1, cols=2)
    _no_borders(t)
    t.autofit = False
    _col_w(t, pw, [50, 50])

    for j, (lbl, val) in enumerate([(lbl1, val1), (lbl2, val2)]):
        cell = t.cell(0, j)
        _shading(cell, WHITE_HEX)
        _cell_bottom_only(cell, LINE_HEX, "4")
        # Chap: o'ng padding bor, o'ng: yo'q
        _cell_pad(cell, top=100, bottom=80,
                  left=0, right=280 if j == 0 else 0)

        # Label — 8pt, kichik, letter-spacing
        p_lbl = cell.paragraphs[0]
        _spc(p_lbl, before=0, after=0, line=1.0)
        _run(p_lbl, lbl, bold=False, size=8.0,
             color=LABEL_CLR, lspc=1.5)

        # Qiymat — 11pt, oddiy, label pastida (bo'sh joy yo'q)
        p_val = cell.add_paragraph()
        _spc(p_val, before=0, after=0, line=1.2)
        _run(p_val, val or "", bold=False, size=11.0, color=DARK)


def _info_block_1col(doc, pw, lbl, val):
    """To'liq kenglik info qator (manzil uchun)."""
    t = doc.add_table(rows=1, cols=1)
    _no_borders(t)
    t.autofit = False
    _col_w(t, pw, [100])

    cell = t.cell(0, 0)
    _shading(cell, WHITE_HEX)
    _cell_bottom_only(cell, LINE_HEX, "4")
    _cell_pad(cell, top=100, bottom=80, left=0, right=0)

    p_lbl = cell.paragraphs[0]
    _spc(p_lbl, before=0, after=0, line=1.0)
    _run(p_lbl, lbl, bold=False, size=8.0,
         color=LABEL_CLR, lspc=1.5)

    p_val = cell.add_paragraph()
    _spc(p_val, before=0, after=0, line=1.2)
    _run(p_val, val or "", bold=False, size=11.0, color=DARK)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_obyektivka_docx(user_data: dict, photo_path: str,
                              output_filepath: str) -> str:
    lang = user_data.get("lang", "uz_lat") or "uz_lat"
    lb   = _OBY_LBL.get(lang, _OBY_LBL["uz_lat"])
    g    = user_data.get

    doc = Document()
    _set_margins(doc)
    ns = doc.styles["Normal"]
    ns.font.name = FONT
    ns.font.size = Pt(11)
    ns.paragraph_format.space_before = Pt(0)
    ns.paragraph_format.space_after  = Pt(0)

    pw = _pw(doc)

    # ═══════════════════════════════════════════════════════
    # 1. SARLAVHA — markazda, qalin, katta harf
    # ═══════════════════════════════════════════════════════
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _spc(p_title, before=0, after=22, line=1.0)
    _run(p_title, lb["title"], bold=True, size=16.0, color=BLACK, lspc=4.0)

    # ═══════════════════════════════════════════════════════
    # 2. NAME BLOK | FOTO
    # Nisbat: chap 75% (ism), o'ng 25% (foto)
    # Foto: rasm bo'lsa chegara yo'q, bo'lmasa punktir
    # ═══════════════════════════════════════════════════════
    hdr = doc.add_table(rows=1, cols=2)
    _no_borders(hdr)
    hdr.autofit = False
    _col_w(hdr, pw, [75, 25])

    # Chap: F.I.SH label + katta ism
    nc = hdr.cell(0, 0)
    _shading(nc, WHITE_HEX)
    _cell_no_borders(nc)
    _cell_pad(nc, top=0, bottom=0, left=0, right=0)

    p_lbl = nc.paragraphs[0]
    _spc(p_lbl, before=0, after=4, line=1.0)
    _run(p_lbl, lb["name_lbl"], bold=False, size=8.0,
         color=LABEL_CLR, lspc=1.5)

    p_nm = nc.add_paragraph()
    _spc(p_nm, before=3, after=0, line=1.2)
    fullname = (g("fullname", "") or "").upper()
    _run(p_nm, fullname, bold=True, size=15.0, color=BLACK)

    # O'ng: foto ustuni
    pc = hdr.cell(0, 1)
    _shading(pc, WHITE_HEX)

    has_photo = photo_path and os.path.exists(photo_path)

    if has_photo:
        # Rasm bor — chegara yo'q, minimal padding
        _cell_no_borders(pc)
        _cell_pad(pc, top=0, bottom=0, left=60, right=0)
    else:
        # Placeholder — punktir chegara
        _cell_dashed_all(pc, "BBBBBB", "6")
        _cell_pad(pc, top=80, bottom=80, left=60, right=0)

    _vcenter(pc)
    p_ph = pc.paragraphs[0]
    p_ph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _spc(p_ph, before=0, after=0, line=1.0)

    if has_photo:
        r = p_ph.add_run()
        # 3x4 sm = 30x40 mm
        r.add_picture(photo_path, width=Mm(28), height=Mm(37))
    else:
        p_ph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(p_ph, lb["photo"], bold=False, size=9.0, color=MUTED)

    # Header va info orasidagi bo'sh joy
    sp1 = doc.add_paragraph()
    _spc(sp1, before=0, after=22)

    # ═══════════════════════════════════════════════════════
    # 3. INFO QATORLARI
    # ═══════════════════════════════════════════════════════
    pairs = [
        (lb["bdate"],   g("birthdate","")            or g("bdate",""),
         lb["bplace"],  g("birthplace","")           or g("bplace","")),
        (lb["nation"],  g("nation",""),
         lb["party"],   g("party","")),
        (lb["edu"],     g("education","")            or g("edu",""),
         lb["grad"],    g("graduated","")            or g("grad","")),
        (lb["spec"],    g("specialty","")            or g("spec",""),
         lb["degree"],  g("degree","")),
        (lb["stitle"],  g("scientific_title","")     or g("stitle",""),
         lb["langs"],   g("languages","")            or g("langs","")),
        (lb["military"],g("military_rank","")        or g("military",""),
         lb["awards"],  g("awards","")),
        (lb["deputy"],  g("deputy",""),
         lb["phone"],   g("phone","")),
    ]

    for lbl1, val1, lbl2, val2 in pairs:
        _info_block_2col(doc, pw, lbl1, val1, lbl2, val2)

    _info_block_1col(doc, pw, lb["addr"],
                     g("address","") or g("addr",""))

    # ═══════════════════════════════════════════════════════
    # 4. MEHNAT FAOLIYATI
    # ═══════════════════════════════════════════════════════
    sp2 = doc.add_paragraph()
    _spc(sp2, before=0, after=18)

    _sect_title(doc, lb["exp_title"])

    works = g("work_experience", []) or []

    if not works:
        p_nd = doc.add_paragraph()
        p_nd.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _spc(p_nd, before=8, after=8, line=1.0)
        _run(p_nd, lb["no_data"], italic=True, size=10.5, color=ITALIC_C)
    else:
        wtbl = doc.add_table(rows=1 + len(works), cols=2)
        _no_borders(wtbl)
        wtbl.autofit = False
        _col_w(wtbl, pw, [25, 75])

        # Header qator
        for j, ht in enumerate([lb["exp_col1"], lb["exp_col2"]]):
            hc = wtbl.cell(0, j)
            _shading(hc, GREY_HEX)
            _cell_bottom_only(hc, "999999", "6")
            _cell_pad(hc, top=80, bottom=80,
                      left=0 if j == 0 else 120, right=0)
            hp = hc.paragraphs[0]
            _spc(hp, before=0, after=0, line=1.0)
            _run(hp, ht, bold=False, size=8.0,
                 color=LABEL_CLR, lspc=1.0)

        # Ma'lumot qatorlari
        for i, work in enumerate(works):
            year = work.get("year","") or work.get("years","") or ""
            pos  = work.get("position","") or work.get("pos","") or ""
            for j, (cell, val) in enumerate([
                (wtbl.cell(1+i, 0), year),
                (wtbl.cell(1+i, 1), pos),
            ]):
                _shading(cell, WHITE_HEX)
                _cell_bottom_only(cell, LINE_HEX, "4")
                _cell_pad(cell, top=90, bottom=90,
                          left=0 if j == 0 else 120, right=0)
                cp = cell.paragraphs[0]
                _spc(cp, before=0, after=0, line=1.15)
                _run(cp, val, size=11.0, color=DARK)

    # ═══════════════════════════════════════════════════════
    # 5. YAQIN QARINDOSHLARI
    # ═══════════════════════════════════════════════════════
    sp3 = doc.add_paragraph()
    _spc(sp3, before=0, after=18)

    fname = (g("fullname","") or "").split()[0].upper() \
            if g("fullname","") else ""
    if lang == "ru":
        rel_title = lb["rel_suffix"]
    else:
        rel_title = f"{fname} {lb['rel_suffix']}" if fname else lb["rel_suffix"]

    _sect_title(doc, rel_title)

    rels = g("relatives", []) or []

    if not rels:
        p_nd2 = doc.add_paragraph()
        p_nd2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _spc(p_nd2, before=8, after=8, line=1.0)
        _run(p_nd2, lb["no_data"], italic=True, size=10.5, color=ITALIC_C)
    else:
        rtbl = doc.add_table(rows=1 + len(rels), cols=5)
        _no_borders(rtbl)
        rtbl.autofit = False
        _col_w(rtbl, pw, [13, 19, 18, 28, 22])

        for j, h in enumerate([lb["rel_c1"], lb["rel_c2"], lb["rel_c3"],
                                lb["rel_c4"], lb["rel_c5"]]):
            hc = rtbl.cell(0, j)
            _shading(hc, GREY_HEX)
            _cell_all_borders(hc, "999999", "4")
            _cell_pad(hc, top=80, bottom=80, left=80, right=80)
            hcp = hc.paragraphs[0]
            hcp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _spc(hcp, before=0, after=0, line=1.1)
            _run(hcp, h, bold=False, size=7.5, color=LABEL_CLR, lspc=0.5)

        for i, rel in enumerate(rels):
            vals = [
                rel.get("degree","")           or rel.get("kin",""),
                rel.get("fullname","")          or rel.get("fish",""),
                rel.get("birth_year_place","")  or rel.get("birth",""),
                rel.get("work_place","")        or rel.get("work",""),
                rel.get("address","")           or rel.get("addr",""),
            ]
            for j, val in enumerate(vals):
                rc = rtbl.cell(1+i, j)
                _shading(rc, WHITE_HEX)
                _cell_all_borders(rc, LINE_HEX, "4")
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
    # Rasmga mos — ba'zi qiymatlari bor, ba'zilari yo'q
    sample = {
        "lang":      "uz_lat",
        "fullname":  "Asad",
        "birthdate": "",
        "birthplace":"Sad",
        "nation":    "Sda",
        "party":     "",
        "education": "",
        "graduated": "",
        "specialty": "",
        "degree":    "",
        "scientific_title": "",
        "languages": "",
        "military":  "",
        "awards":    "",
        "deputy":    "",
        "phone":     "",
        "address":   "",
        "work_experience": [],
        "relatives": [],
    }
    out = generate_obyektivka_docx(sample, "", "/home/claude/test_v6.docx")
    print(f"✓ Saved: {out}")

    # To'liq ma'lumot bilan ham test
    sample_full = {
        "lang":      "uz_lat",
        "fullname":  "Karimov Jasur Abdullayevich",
        "birthdate": "15.03.1985",
        "birthplace":"Toshkent shahri",
        "nation":    "O'zbek",
        "party":     "Yo'q",
        "education": "Oliy",
        "graduated": "TDTU",
        "specialty": "Muhandis",
        "degree":    "PhD",
        "scientific_title": "Dotsent",
        "languages": "Ingliz, Rus",
        "military":  "Leytenant",
        "awards":    "Mehnat shuhrati",
        "deputy":    "Yo'q",
        "phone":     "+998 90 123 45 67",
        "address":   "Toshkent sh., Yunusobod tumani, 14-mavze, 22-uy",
        "work_experience": [
            {"year": "2005–2010", "position": "TDTU — Muhandis"},
            {"year": "2010–2015", "position": "Texnopark MChJ — Bosh muhandis"},
            {"year": "2015–hozir","position": "O'zbekiston FA — Lab. mudiri"},
        ],
        "relatives": [
            {"degree": "Xotini", "fullname": "Karimova Dilnoza",
             "birth_year_place": "1987, Toshkent",
             "work_place": "1-maktab, o'qituvchi",
             "address": "Toshkent, Yunusobod"},
        ],
    }
    out2 = generate_obyektivka_docx(sample_full, "", "/home/claude/test_v6_full.docx")
    print(f"✓ To'liq: {out2}")