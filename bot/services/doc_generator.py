"""
Professional Obyektivka (Resume) Generator
Generates beautifully formatted Word and PDF documents.
"""
import base64
import json
import logging
import os
from io import BytesIO
from typing import Any, Dict, List, Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.shared import Cm, Pt, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph, Spacer, Table, TableStyle,
    PageBreak, SimpleDocTemplate, Image as RLImage
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

# ── Font registration ─────────────────────────────────────────────────────────
REG  = 'DV'
BOLD = 'DV-Bold'

_font_registered = False
_linux_fonts = [
    ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
     '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
    ('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
     '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'),
    ('/usr/share/fonts/truetype/freefont/FreeSans.ttf',
     '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf'),
]

for _reg_path, _bold_path in _linux_fonts:
    if os.path.exists(_reg_path) and os.path.exists(_bold_path):
        try:
            pdfmetrics.registerFont(TTFont(REG,  _reg_path))
            pdfmetrics.registerFont(TTFont(BOLD, _bold_path))
            _font_registered = True
            break
        except Exception:
            pass

if not _font_registered:
    # Fall back to built-in Helvetica (no Cyrillic, but won't crash)
    REG  = 'Helvetica'
    BOLD = 'Helvetica-Bold'

# ── Page constants ────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = A4
ML = 2.5 * cm
MR = 1.5 * cm
MT = 2.0 * cm
MB = 2.0 * cm
CW = PAGE_W - ML - MR   # usable content width

BORDER  = colors.black
BG_WORK = colors.HexColor('#E8E8E8')

# ── Labels ────────────────────────────────────────────────────────────────────
LABELS = {
    'uz_l': {
        'title':      "MA'LUMOTNOMA",
        'birthdate':  "Tug'ilgan yili:",
        'birthplace': "Tug'ilgan joyi:",
        'nation':     "Millati:",
        'party':      "Partiyaviyligi:",
        'education':  "Ma'lumoti:",
        'graduated':  "Tamomlagan:",
        'specialty':  "Ma'lumoti bo'yicha mutaxassisligi:",
        'degree':     "Ilmiy darajasi:",
        'scititle':   "Ilmiy unvoni:",
        'langs':      "Qaysi chet tillarini biladi:",
        'military':   "Harbiy unvoni:",
        'awards':     "Davlat mukofotlari bilan taqdirlanganmi (qanaqa):",
        'deputy':     "Xalq deputatlari respublika, viloyat, shahar va tuman Kengashi deputatimi yoki boshqa saylanadigan organlarning a'zosimi (to'liq ko'rsatilishi lozim):",
        'work_title': "MEHNAT FAOLIYATI",
        'rel_title_suffix': "ning yaqin qarindoshlari haqida",
        'rel_subtitle':     "MA'LUMOTNOMA",
        'rel_col1':   "Qarindoshligi",
        'rel_col2':   "Familiyasi ismi va\notasining ismi",
        'rel_col3':   "Tug'ilgan yili\nva joyi",
        'rel_col4':   "Ish joyi va\nlavozimi",
        'rel_col5':   "Turar joyi",
        'rel_empty':  "Qarindoshlar qo'shilmagan",
        'work_empty': "Ish joylari qo'shilmagan",
        'sample_watermark': "NAMUNA",
    },
    'uz_k': {
        'title':      "\u041c\u0410\u042a\u041b\u0423\u041c\u041e\u0422\u041d\u041e\u041c\u0410",
        'birthdate':  "\u0422\u0443\u0493\u0438\u043b\u0433\u0430\u043d \u0439\u0438\u043b\u0438:",
        'birthplace': "\u0422\u0443\u0493\u0438\u043b\u0433\u0430\u043d \u0436\u043e\u0439\u0438:",
        'nation':     "\u041c\u0438\u043b\u043b\u0430\u0442\u0438:",
        'party':      "\u041f\u0430\u0440\u0442\u0438\u044f\u0432\u0438\u0439\u043b\u0438\u0433\u0438:",
        'education':  "\u041c\u0430\u044a\u043b\u0443\u043c\u043e\u0442\u0438:",
        'graduated':  "\u0422\u0430\u043c\u043e\u043c\u043b\u0430\u0433\u0430\u043d:",
        'specialty':  "\u041c\u0430\u044a\u043b\u0443\u043c\u043e\u0442\u0438 \u0431\u045e\u0439\u0438\u0447\u0430 \u043c\u0443\u0442\u0430\u0445\u0430\u0441\u0441\u0438\u0441\u043b\u0438\u0433\u0438:",
        'degree':     "\u0418\u043b\u043c\u0438\u0439 \u0434\u0430\u0440\u0430\u0436\u0430\u0441\u0438:",
        'scititle':   "\u0418\u043b\u043c\u0438\u0439 \u0443\u043d\u0432\u043e\u043d\u0438:",
        'langs':      "\u049a\u0430\u0439\u0441\u0438 \u0447\u0435\u0442 \u0442\u0438\u043b\u043b\u0430\u0440\u0438\u043d\u0438 \u0431\u0438\u043b\u0430\u0434\u0438:",
        'military':   "\u04b2\u0430\u0440\u0431\u0438\u0439 \u0443\u043d\u0432\u043e\u043d\u0438:",
        'awards':     "\u0414\u0430\u0432\u043b\u0430\u0442 \u043c\u0443\u043a\u043e\u0444\u043e\u0442\u043b\u0430\u0440\u0438 \u0431\u0438\u043b\u0430\u043d \u0442\u0430\u049b\u0434\u0438\u0440\u043b\u0430\u043d\u0433\u0430\u043d\u043c\u0438 (\u049b\u0430\u043d\u0430\u049b\u0430):",
        'deputy':     "\u0425\u0430\u043b\u049b \u0434\u0435\u043f\u0443\u0442\u0430\u0442\u043b\u0430\u0440\u0438 \u0440\u0435\u0441\u043f\u0443\u0431\u043b\u0438\u043a\u0430, \u0432\u0438\u043b\u043e\u044f\u0442, \u0448\u0430\u04b3\u0430\u0440 \u0432\u0430 \u0442\u0443\u043c\u0430\u043d \u041a\u0435\u043d\u0433\u0430\u0448\u0438 \u0434\u0435\u043f\u0443\u0442\u0430\u0442\u0438\u043c\u0438 \u0451\u043a\u0438 \u0431\u043e\u0448\u049b\u0430 \u0441\u0430\u0439\u043b\u0430\u043d\u0430\u0434\u0438\u0433\u0430\u043d \u043e\u0440\u0433\u0430\u043d\u043b\u0430\u0440\u043d\u0438\u043d\u0433 \u0430\u044a\u0437\u043e\u0441\u0438\u043c\u0438 (\u0442\u045e\u043b\u0438\u049b \u043a\u045e\u0440\u0441\u0430\u0442\u0438\u043b\u0438\u0448\u0438 \u043b\u043e\u0437\u0438\u043c):",
        'work_title': "\u041c\u0415\u04b2\u041d\u0410\u0422 \u0424\u0410\u041e\u041b\u0418\u042f\u0422\u0418",
        'rel_title_suffix': "\u043d\u0438\u043d\u0433 \u044f\u049b\u0438\u043d \u049b\u0430\u0440\u0438\u043d\u0434\u043e\u0448\u043b\u0430\u0440\u0438 \u04b3\u0430\u049b\u0438\u0434\u0430",
        'rel_subtitle':     "\u041c\u0410\u042a\u041b\u0423\u041c\u041e\u0422\u041d\u041e\u041c\u0410",
        'rel_col1':   "\u049a\u0430\u0440\u0438\u043d\u0434\u043e\u0448\u043b\u0438\u0433\u0438",
        'rel_col2':   "\u0424\u0430\u043c\u0438\u043b\u0438\u044f\u0441\u0438 \u0438\u0441\u043c\u0438 \u0432\u0430\n\u043e\u0442\u0430\u0441\u0438\u043d\u0438\u043d\u0433 \u0438\u0441\u043c\u0438",
        'rel_col3':   "\u0422\u0443\u0493\u0438\u043b\u0433\u0430\u043d \u0439\u0438\u043b\u0438\n\u0432\u0430 \u0436\u043e\u0439\u0438",
        'rel_col4':   "\u0418\u0448 \u0436\u043e\u0439\u0438 \u0432\u0430\n\u043b\u0430\u0432\u043e\u0437\u0438\u043c\u0438",
        'rel_col5':   "\u0422\u0443\u0440\u0430\u0440 \u0436\u043e\u0439\u0438",
        'rel_empty':  "\u049a\u0430\u0440\u0438\u043d\u0434\u043e\u0448\u043b\u0430\u0440 \u049b\u045e\u0448\u0438\u043b\u043c\u0430\u0433\u0430\u043d",
        'work_empty': "\u0418\u0448 \u0436\u043e\u0439\u043b\u0430\u0440\u0438 \u049b\u045e\u0448\u0438\u043b\u043c\u0430\u0433\u0430\u043d",
        'sample_watermark': "\u041d\u0410\u041c\u0423\u041d\u0410",
    }
}


def _ps(name, **kw) -> ParagraphStyle:
    ps = ParagraphStyle(name)
    defaults = dict(fontName=REG, fontSize=10, leading=14,
                    textColor=colors.black, spaceAfter=0, spaceBefore=0)
    defaults.update(kw)
    for k, val in defaults.items():
        setattr(ps, k, val)
    return ps


def _parse_json_field(field_value) -> List[Dict]:
    if not field_value:
        return []
    try:
        if isinstance(field_value, str):
            return json.loads(field_value)
        elif isinstance(field_value, list):
            return field_value
        return []
    except (json.JSONDecodeError, TypeError):
        return []


def _decode_photo(photo_data: str) -> Optional[BytesIO]:
    if not photo_data:
        return None
    try:
        if str(photo_data).startswith(('http://', 'https://')):
            import requests
            response = requests.get(photo_data, timeout=10)
            response.raise_for_status()
            return BytesIO(response.content)
        if 'base64,' in photo_data:
            photo_data = photo_data.split('base64,')[1]
        return BytesIO(base64.b64decode(photo_data))
    except Exception as e:
        logger.warning(f"Failed to decode/download photo: {e}")
        return None


def latin_to_cyrillic(text: str) -> str:
    if not text:
        return ""
    for lat, cyr in [
        ("Ya", "\u042f"), ("ya", "\u044f"), ("Yu", "\u042e"), ("yu", "\u044e"),
        ("Sh", "\u0428"), ("sh", "\u0448"), ("Ch", "\u0427"), ("ch", "\u0447"),
        ("O'", "\u040e"), ("o'", "\u045e"), ("G'", "\u0492"), ("g'", "\u0493"),
        ("Yo", "\u0401"), ("yo", "\u0451"),
    ]:
        text = text.replace(lat, cyr)
    mapping = {
        "A": "\u0410", "a": "\u0430", "B": "\u0411", "b": "\u0431",
        "D": "\u0414", "d": "\u0434", "E": "\u0415", "e": "\u0435",
        "F": "\u0424", "f": "\u0444", "G": "\u0413", "g": "\u0433",
        "H": "\u04b2", "h": "\u04b3", "I": "\u0418", "i": "\u0438",
        "J": "\u0416", "j": "\u0436", "K": "\u041a", "k": "\u043a",
        "L": "\u041b", "l": "\u043b", "M": "\u041c", "m": "\u043c",
        "N": "\u041d", "n": "\u043d", "O": "\u041e", "o": "\u043e",
        "P": "\u041f", "p": "\u043f", "Q": "\u049a", "q": "\u049b",
        "R": "\u0420", "r": "\u0440", "S": "\u0421", "s": "\u0441",
        "T": "\u0422", "t": "\u0442", "U": "\u0423", "u": "\u0443",
        "V": "\u0412", "v": "\u0432", "X": "\u0425", "x": "\u0445",
        "Y": "\u0419", "y": "\u0439", "Z": "\u0417", "z": "\u0437",
        "'": "\u044a",
    }
    return "".join(mapping.get(c, c) for c in text)


# =============================================================================
# PDF GENERATOR  (klassik shablon)
# =============================================================================

def generate_obyektivka_pdf(data: Dict[str, Any],
                             lang: str = 'uz_l',
                             is_sample: bool = False) -> BytesIO:

    lb  = LABELS.get(lang, LABELS['uz_l'])
    out = BytesIO()

    doc = SimpleDocTemplate(
        out, pagesize=A4,
        topMargin=MT, bottomMargin=MB,
        leftMargin=ML, rightMargin=MR,
    )

    # Styles
    title_s = _ps('title', fontName=BOLD, fontSize=13, alignment=TA_CENTER, leading=18)
    name_s  = _ps('name',  fontName=BOLD, fontSize=13, alignment=TA_CENTER, leading=18, spaceAfter=8)
    cell_s  = _ps('cell',  fontName=REG,  fontSize=10, leading=14)
    sec_s   = _ps('sec',   fontName=BOLD, fontSize=11, alignment=TA_CENTER, leading=16)
    work_s  = _ps('work',  fontName=REG,  fontSize=10, leading=14)
    rel_h_s = _ps('relh',  fontName=BOLD, fontSize=9.5, alignment=TA_CENTER, leading=13)
    rel_v_s = _ps('relv',  fontName=REG,  fontSize=9.5, alignment=TA_CENTER, leading=13)
    rel_t_s = _ps('relt',  fontName=BOLD, fontSize=9.5, alignment=TA_CENTER, leading=13)

    fullname = (data.get('fullname') or '').strip()
    story    = []

    # Watermark
    if is_sample:
        story.append(Paragraph(
            "<font color='red'><b>" + lb.get('sample_watermark', 'NAMUNA') + "</b></font>",
            _ps('wm', fontName=BOLD, fontSize=22, alignment=TA_CENTER)
        ))
        story.append(Spacer(1, 0.2 * cm))

    story.append(Paragraph(lb['title'], title_s))
    story.append(Paragraph(fullname, name_s))

    # Helper
    def v(k):
        return (data.get(k) or '').strip() or "yo'q"

    def C(label, value):
        val = (str(value) or '').strip() or "yo'q"
        return Paragraph(f"<b>{label}</b><br/>{val}", cell_s)

    # Photo
    photo_w   = 3.2 * cm
    C0        = (CW - photo_w) / 2
    C1        = CW - photo_w - C0

    photo_cell = Paragraph('', cell_s)
    ps_stream  = _decode_photo((data.get('photo_data') or '').strip())
    if ps_stream:
        try:
            from PIL import Image as PIL_IMG
            img = PIL_IMG.open(ps_stream)
            buf = BytesIO()
            img.save(buf, 'PNG')
            buf.seek(0)
            photo_cell = RLImage(buf, width=2.8 * cm, height=3.6 * cm)
        except Exception:
            pass

    tdata = [
        [C(lb['birthdate'],  v('birthdate')),
         C(lb['birthplace'], v('birthplace')),
         photo_cell],
        [C(lb['nation'],     v('nation')),
         C(lb['party'],      v('party')),
         ''],
        [C(lb['education'],  v('education')),
         C(lb['graduated'],  v('graduated')),
         ''],
        [C(lb['specialty'],  v('specialty')), '', ''],
        [C(lb['degree'],     v('degree')),
         C(lb['scititle'],   v('scientific_title')),
         ''],
        [C(lb['langs'],      v('languages')),
         C(lb['military'],   v('military_rank')),
         ''],
        [C(lb['awards'],     v('awards')), '', ''],
        [C(lb['deputy'],     v('deputy')), '', ''],
    ]

    ts = [
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('SPAN',  (2, 0), (2, 2)),
        ('VALIGN',(2, 0), (2, 0), 'MIDDLE'),
        ('ALIGN', (2, 0), (2, 0), 'CENTER'),
        ('SPAN',  (0, 3), (2, 3)),
        ('SPAN',  (0, 6), (2, 6)),
        ('SPAN',  (0, 7), (2, 7)),
    ]

    main_t = Table(tdata, colWidths=[C0, C1, photo_w])
    main_t.setStyle(TableStyle(ts))
    story.append(main_t)
    story.append(Spacer(1, 0.3 * cm))

    # Work experience
    work_exp = _parse_json_field(data.get('work_experience'))

    wh = Table([[Paragraph(lb['work_title'], sec_s)]], colWidths=[CW])
    wh.setStyle(TableStyle([
        ('BOX',           (0, 0), (-1, -1), 0.7, BORDER),
        ('BACKGROUND',    (0, 0), (-1, -1), BG_WORK),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 5),
    ]))
    story.append(wh)

    if work_exp:
        rows = []
        for w in work_exp:
            yr  = (w.get('year') or '').strip()
            pos = (w.get('position') or w.get('description') or '').strip()
            if not (yr or pos):
                continue
            txt = (f'<b>{yr} yy.</b> - ' if yr else '') + pos
            rows.append([Paragraph(txt, work_s)])
        if rows:
            wt = Table(rows, colWidths=[CW])
            wt.setStyle(TableStyle([
                ('BOX',           (0, 0), (-1, -1), 0.7, BORDER),
                ('LINEBELOW',     (0, 0), (-1, -2), 0.5, BORDER),
                ('TOPPADDING',    (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING',   (0, 0), (-1, -1), 6),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
            ]))
            story.append(wt)
    else:
        et = Table([[Paragraph(lb['work_empty'], cell_s)]], colWidths=[CW])
        et.setStyle(TableStyle([
            ('BOX',         (0, 0), (-1, -1), 0.7, BORDER),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING',  (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING',(0, 0),(-1, -1), 4),
        ]))
        story.append(et)

    # Relatives — page 2
    story.append(PageBreak())

    story.append(Paragraph(
        f"{fullname}{lb['rel_title_suffix']}",
        _ps('rt2', fontName=BOLD, fontSize=11, alignment=TA_CENTER, leading=16, spaceAfter=3)
    ))
    story.append(Paragraph(
        lb['rel_subtitle'],
        _ps('rs', fontName=BOLD, fontSize=12, alignment=TA_CENTER, leading=16, spaceAfter=10)
    ))

    relatives = _parse_json_field(data.get('relatives'))
    RC  = [3.2 * cm, 4.0 * cm, 3.3 * cm, 3.5 * cm, 3.0 * cm]
    hdr = [Paragraph(lb[k], rel_h_s) for k in
           ('rel_col1', 'rel_col2', 'rel_col3', 'rel_col4', 'rel_col5')]
    rel_rows = [hdr]

    if relatives:
        for r in relatives:
            rel_rows.append([
                Paragraph((r.get('type')  or ''), rel_t_s),
                Paragraph((r.get('name')  or ''), rel_v_s),
                Paragraph((r.get('birth') or ''), rel_v_s),
                Paragraph((r.get('job')   or ''), rel_v_s),
                Paragraph((r.get('addr')  or ''), rel_v_s),
            ])
    else:
        rel_rows.append([Paragraph(lb['rel_empty'], rel_v_s), '', '', '', ''])

    rts = [
        ('GRID',          (0, 0), (-1, -1), 0.7, BORDER),
        ('BACKGROUND',    (0, 0), (-1, 0),  BG_WORK),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
    ]
    if not relatives:
        rts.append(('SPAN', (0, 1), (4, 1)))

    rel_t = Table(rel_rows, colWidths=RC)
    rel_t.setStyle(TableStyle(rts))
    story.append(rel_t)

    doc.build(story)
    out.seek(0)
    return out


# =============================================================================
# WORD GENERATOR
# =============================================================================

class ObyektivkaGenerator:

    def __init__(self, data: Dict[str, Any], lang: str = 'uz_l', is_sample: bool = False):
        self.data      = data
        self.lang      = lang if lang in LABELS else 'uz_l'
        self.labels    = LABELS[self.lang]
        self.is_sample = is_sample

        self.fullname        = data.get('fullname', '').strip()
        self.birthdate       = data.get('birthdate', '').strip()
        self.birthplace      = data.get('birthplace', '').strip()
        self.nation          = data.get('nation', '').strip()
        self.education       = data.get('education', '').strip()
        self.specialty       = data.get('specialty', '').strip()
        self.degree          = data.get('degree', '').strip()
        self.languages       = data.get('languages', '').strip()
        self.awards          = data.get('awards', '').strip()
        self.deputy          = data.get('deputy', '').strip()
        self.party           = data.get('party', '').strip()
        self.graduated       = data.get('graduated', '').strip()
        self.scientific_title= data.get('scientific_title', '').strip()
        self.military_rank   = data.get('military_rank', '').strip()
        self.photo_data      = data.get('photo_data', '').strip()

        self.work_experience = _parse_json_field(data.get('work_experience', '[]'))
        self.relatives       = _parse_json_field(data.get('relatives', '[]'))

    def _transliterate_if_needed(self, text: str) -> str:
        if not text:
            return ""
        if self.lang == 'uz_k':
            return latin_to_cyrillic(text)
        return text

    def generate_word(self) -> BytesIO:
        doc = Document()

        for section in doc.sections:
            section.top_margin    = Cm(1.5)
            section.bottom_margin = Cm(1.5)
            section.left_margin   = Cm(2)
            section.right_margin  = Cm(1.5)

        style      = doc.styles['Normal']
        style.font.name = 'Times New Roman'
        style.font.size = Pt(12)

        if self.is_sample:
            p   = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(self.labels.get('sample_watermark', 'NAMUNA'))
            run.bold = True
            run.font.size = Pt(24)
            run.font.color.rgb = RGBColor(255, 0, 0)

        def add_item(paragraph, label, value):
            run = paragraph.add_run(f"{label}\n")
            run.bold = True
            paragraph.add_run(f"{value}")
            paragraph.paragraph_format.space_after = Pt(6)

        def _remove_table_borders(table_obj):
            tbl   = table_obj._tbl
            tblPr = tbl.tblPr
            if tblPr is None:
                tblPr = OxmlElement("w:tblPr")
                tbl.insert(0, tblPr)
            tblBorders = OxmlElement("w:tblBorders")
            for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
                border = OxmlElement(f"w:{side}")
                border.set(qn("w:val"), "none")
                border.set(qn("w:sz"), "0")
                border.set(qn("w:space"), "0")
                border.set(qn("w:color"), "auto")
                tblBorders.append(border)
            tblPr.append(tblBorders)

        # Title
        title = doc.add_paragraph(self.labels['title'])
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title.runs[0].bold = True
        title.runs[0].font.size = Pt(14)

        name_para = doc.add_paragraph()
        name_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = name_para.add_run(self.fullname)
        run.bold = True
        run.font.size = Pt(14)
        name_para.paragraph_format.space_after = Pt(12)

        table = doc.add_table(rows=0, cols=3)
        table.autofit = False
        table.allow_autofit = False
        table.columns[0].width = Cm(7)
        table.columns[1].width = Cm(7)
        table.columns[2].width = Cm(3.5)

        row = table.add_row()
        add_item(row.cells[0].paragraphs[0], self.labels['birthdate'],  self.birthdate)
        add_item(row.cells[1].paragraphs[0], self.labels['birthplace'], self.birthplace)

        row2 = table.add_row()
        add_item(row2.cells[0].paragraphs[0], self.labels['nation'], self.nation)
        add_item(row2.cells[1].paragraphs[0], self.labels['party'],  self.party)

        row3 = table.add_row()
        add_item(row3.cells[0].paragraphs[0], self.labels['education'], self.education)
        add_item(row3.cells[1].paragraphs[0], self.labels['graduated'], self.graduated)

        photo_cell = table.cell(0, 2)
        photo_cell.merge(table.cell(2, 2))
        ps = _decode_photo(self.photo_data)
        if ps:
            try:
                p   = photo_cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.add_run()
                run.add_picture(ps, width=Cm(3), height=Cm(4))
            except Exception:
                pass

        row4 = table.add_row()
        add_item(row4.cells[0].paragraphs[0], self.labels['specialty'], self.specialty)
        row4.cells[0].merge(row4.cells[1])

        row5 = table.add_row()
        add_item(row5.cells[0].paragraphs[0], self.labels['degree'],   self.degree)
        add_item(row5.cells[1].paragraphs[0], self.labels['scititle'], self.scientific_title)

        row6 = table.add_row()
        add_item(row6.cells[0].paragraphs[0], self.labels['langs'],    self.languages)
        add_item(row6.cells[1].paragraphs[0], self.labels['military'], self.military_rank)

        row7 = table.add_row()
        add_item(row7.cells[0].paragraphs[0], self.labels['awards'], self.awards)
        row7.cells[0].merge(row7.cells[2])

        row8 = table.add_row()
        add_item(row8.cells[0].paragraphs[0], self.labels['deputy'], self.deputy)
        row8.cells[0].merge(row8.cells[2])

        _remove_table_borders(table)
        doc.add_paragraph()

        work_title = doc.add_paragraph(self.labels['work_title'])
        work_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        work_title.runs[0].bold = True

        if self.work_experience:
            work_table = doc.add_table(rows=0, cols=1)
            work_table.autofit       = False
            work_table.allow_autofit = False
            work_table.columns[0].width = Cm(17.5)
            for work in self.work_experience:
                year = work.get('year', '').strip()
                desc = work.get('position', work.get('description', '')).strip()
                if year or desc:
                    row  = work_table.add_row()
                    cell = row.cells[0]
                    p    = cell.paragraphs[0]
                    if year:
                        r_year = p.add_run(year)
                        r_year.bold = True
                        p.add_run(" - ")
                    p.add_run(desc)
                    p.paragraph_format.space_after = Pt(2)
            _remove_table_borders(work_table)

        doc.add_page_break()

        rel_title = doc.add_paragraph(f"{self.fullname}{self.labels['rel_title_suffix']}")
        rel_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rel_title.runs[0].bold = True

        rel_subtitle = doc.add_paragraph(self.labels['rel_subtitle'])
        rel_subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rel_subtitle.runs[0].bold = True

        headers = [self.labels[k] for k in
                   ('rel_col1', 'rel_col2', 'rel_col3', 'rel_col4', 'rel_col5')]
        rel_table = doc.add_table(rows=1, cols=5)
        rel_table.style = 'Table Grid'

        hdr_cells = rel_table.rows[0].cells
        for i, h in enumerate(headers):
            hdr_cells[i].text = h
            hdr_cells[i].paragraphs[0].runs[0].bold = True
            hdr_cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        if self.relatives:
            for relative in self.relatives:
                row = rel_table.add_row()
                row.cells[0].text = self._transliterate_if_needed(relative.get('type', ''))
                row.cells[1].text = self._transliterate_if_needed(relative.get('name', ''))
                row.cells[2].text = self._transliterate_if_needed(relative.get('birth', ''))
                row.cells[3].text = self._transliterate_if_needed(relative.get('job', ''))
                row.cells[4].text = self._transliterate_if_needed(relative.get('addr', ''))
                for i, cell in enumerate(row.cells):
                    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                    for paragraph in cell.paragraphs:
                        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        if i == 0:
                            for run in paragraph.runs:
                                run.bold = True
                        for run in paragraph.runs:
                            run.font.size = Pt(11)
                            run.font.name = 'Times New Roman'
        else:
            row_cells  = rel_table.add_row().cells
            merged     = row_cells[0].merge(row_cells[4])
            merged.text = self.labels['rel_empty']
            for paragraph in merged.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

        output = BytesIO()
        doc.save(output)
        output.seek(0)
        return output


# =============================================================================
# Public API
# =============================================================================

def generate_obyektivka_word(data: Dict[str, Any],
                              lang: str = 'uz_l',
                              is_sample: bool = False) -> BytesIO:
    raw_lang = str(data.get('lang', lang) or lang)
    if raw_lang in ('uz_lat', 'uz_latin'):
        lang = 'uz_l'
    elif raw_lang in ('uz_cyr', 'uz_kirill'):
        lang = 'uz_k'
    generator = ObyektivkaGenerator(data, lang=lang, is_sample=is_sample)
    return generator.generate_word()


def generate_obyektivka_docx(data: Dict[str, Any],
                              photo_path: Optional[str] = None,
                              output_dir: str = "temp") -> str:
    os.makedirs(output_dir, exist_ok=True)
    raw_lang = str(data.get("lang", "uz_lat") or "uz_lat")
    if raw_lang in ("uz_lat", "uz_latin"):
        lang = "uz_l"
    elif raw_lang in ("uz_cyr", "uz_kirill"):
        lang = "uz_k"
    else:
        lang = "uz_l"

    generator  = ObyektivkaGenerator(data, lang=lang, is_sample=False)
    doc_stream = generator.generate_word()

    safe_name = (data.get("fullname") or "Obyektivka").replace(" ", "_").replace("/", "_")[:30]
    filepath  = os.path.join(output_dir, f"obyektivka_{safe_name}_@DastyorAiBot.docx")
    with open(filepath, "wb") as f:
        f.write(doc_stream.getvalue())
    return filepath


def generate_cv_docx(data: Dict[str, Any], output_dir: str = "temp") -> str:
    from bot.keyboards.doc_generator import generate_cv_docx as _gen
    os.makedirs(output_dir, exist_ok=True)
    return _gen(data, output_dir=output_dir)


def convert_to_pdf_safe(docx_path: str, output_dir: str = "temp") -> Optional[str]:
    if not docx_path or not os.path.exists(docx_path):
        return None
    pdf_path = docx_path.replace(".docx", ".pdf")
    os.makedirs(output_dir, exist_ok=True)
    try:
        from docx2pdf import convert
        convert(docx_path, pdf_path)
        if os.path.exists(pdf_path):
            return pdf_path
    except Exception as e:
        logger.debug(f"docx2pdf failed: {e}")
    try:
        import subprocess
        subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf",
             docx_path, "--outdir", output_dir],
            check=True, timeout=60, capture_output=True,
        )
        if os.path.exists(pdf_path):
            return pdf_path
    except Exception as e:
        logger.debug(f"LibreOffice failed: {e}")
    return None