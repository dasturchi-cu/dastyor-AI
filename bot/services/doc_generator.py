"""
Professional Obyektivka (Resume) Generator
Generates beautifully formatted Word and PDF documents matching the design template.
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
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak, Image, SimpleDocTemplate
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage

logger = logging.getLogger(__name__)

# Define labels for localization
LABELS = {
    'uz_l': {
        'title': "MA'LUMOTNOMA",
        'birthdate': "Tug'ilgan yili:",
        'birthplace': "Tug'ilgan joyi:",
        'nation': "Millati:",
        'party': "Partiyaviyligi:",
        'education': "Ma'lumoti:",
        'graduated': "Tamomlagan:",
        'specialty': "Ma'lumoti bo'yicha mutaxassisligi:",
        'degree': "Ilmiy darajasi:",
        'scititle': "Ilmiy unvoni:",
        'langs': "Qaysi chet tillarini biladi:",
        'military': "Harbiy unvoni:",
        'awards': "Davlat mukofotlari bilan taqdirlanganmi (qanaqa):",
        'deputy': "Xalq deputatlari respublika, viloyat, shahar va tuman Kengashi deputatimi yoki boshqa saylanadigan organlarning a'zosimi (to'liq ko'rsatilishi lozim):",
        'work_title': "MEHNAT FAOLIYATI",
        'work_empty': "Ish joylari qo'shilmagan",
        'rel_title_suffix': "ning yaqin qarindoshlari haqida",
        'rel_subtitle': "MA'LUMOTNOMA",
        'rel_col1': "Qarindoshligi",
        'rel_col2': "Familiyasi ismi va\notasining ismi",
        'rel_col3': "Tug'ilgan yili\nva joyi",
        'rel_col4': "Ish joyi va\nlavozimi",
        'rel_col5': "Turar joyi",
        'rel_empty': "Qarindoshlar qo'shilmagan",
        'sample_watermark': "NAMUNA"
    },
    'uz_k': {
        'title': "МАЪЛУМОТНОМА",
        'birthdate': "Туғилган йили:",
        'birthplace': "Туғилган жойи:",
        'nation': "Миллати:",
        'party': "Партиявийлиги:",
        'education': "Маълумоти:",
        'graduated': "Тамомлаган:",
        'specialty': "Маълумоти бўйича мутахассислиги:",
        'degree': "Илмий даражаси:",
        'scititle': "Илмий унвони:",
        'langs': "Қайси чет тилларини билади:",
        'military': "Ҳарбий унвони:",
        'awards': "Давлат мукофотлари билан тақдирланганми (қанақа):",
        'deputy': "Халқ депутатлари республика, вилоят, шаҳар ва туман Кенгаши депутатими ёки бошқа сайланадиган органларнинг аъзосими (тўлиқ кўрсатилиши лозим):",
        'work_title': "МЕҲНАТ ФАОЛИЯТИ",
        'work_empty': "Иш жойлари қўшилмаган",
        'rel_title_suffix': "нинг яқин қариндошлари ҳақида",
        'rel_subtitle': "МАЪЛУМОТНОМА",
        'rel_col1': "Қариндошлиги",
        'rel_col2': "Фамилияси исми ва\nотасининг исми",
        'rel_col3': "Туғилган йили\nва жойи",
        'rel_col4': "Иш жойи ва\nлавозими",
        'rel_col5': "Турар жойи",
        'rel_empty': "Қариндошлар қўшилмаган",
        'sample_watermark': "НАМУНА"
    }
}

# Register Fonts for Cyrillic support
FONT_NAME_REGULAR = 'Helvetica'
FONT_NAME_BOLD = 'Helvetica-Bold'
CYRILLIC_SUPPORTED = False

try:
    # 1. Try to load local fonts first (user provided)
    local_font_dir = os.path.join(os.path.dirname(__file__), 'fonts')
    times_ttf = os.path.join(local_font_dir, 'times.ttf')
    times_bd_ttf = os.path.join(local_font_dir, 'timesbd.ttf')
    
    if os.path.exists(times_ttf) and os.path.exists(times_bd_ttf):
        pdfmetrics.registerFont(TTFont('Times-Roman', times_ttf))
        pdfmetrics.registerFont(TTFont('Times-Bold', times_bd_ttf))
        FONT_NAME_REGULAR = 'Times-Roman'
        FONT_NAME_BOLD = 'Times-Bold'
        CYRILLIC_SUPPORTED = True
    else:
        # 2. Try Windows system fonts
        win_times = 'C:\\Windows\\Fonts\\times.ttf'
        win_times_bd = 'C:\\Windows\\Fonts\\timesbd.ttf'
        
        if os.path.exists(win_times) and os.path.exists(win_times_bd):
            pdfmetrics.registerFont(TTFont('Times-Roman', win_times))
            pdfmetrics.registerFont(TTFont('Times-Bold', win_times_bd))
            FONT_NAME_REGULAR = 'Times-Roman'
            FONT_NAME_BOLD = 'Times-Bold'
            CYRILLIC_SUPPORTED = True
        else:
            # 3. Try Linux system fonts (DejaVu Sans - common on Render/Linux)
            # List of candidate font paths for Linux
            linux_fonts = [
                # Regular, Bold
                ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
                ('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'),
                ('/usr/share/fonts/truetype/freefont/FreeSans.ttf', '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf'),
            ]
            
            font_found = False
            for reg_path, bold_path in linux_fonts:
                if os.path.exists(reg_path) and os.path.exists(bold_path):
                    # Register as 'CustomFont' to avoid name collision issues
                    pdfmetrics.registerFont(TTFont('CustomFont', reg_path))
                    pdfmetrics.registerFont(TTFont('CustomFont-Bold', bold_path))
                    FONT_NAME_REGULAR = 'CustomFont'
                    FONT_NAME_BOLD = 'CustomFont-Bold'
                    CYRILLIC_SUPPORTED = True
                    font_found = True
                    logger.info(f"Using Linux font: {reg_path}")
                    break
            
            if not font_found:
                 logger.warning("No suitable Cyrillic font found. Falling back to Helvetica.")

except Exception as e:
    logger.warning(f"Could not register system fonts: {e}. Using default fonts (Cyrillic may not display correctly).")
    # FONT_NAME_REGULAR defaults to Helvetica


def latin_to_cyrillic(text: str) -> str:
    """Simple Latin to Cyrillic converter for Uzbek."""
    if not text:
        return ""
    
    mapping = {
        "Ya": "Я", "ya": "я", "Yu": "Ю", "yu": "ю", "Sh": "Ш", "sh": "ш", "Ch": "Ч", "ch": "ч",
        "O'": "Ў", "o'": "ў", "G'": "Ғ", "g'": "ғ", "Yo": "Ё", "yo": "ё",
        "A": "А", "a": "а", "B": "Б", "b": "б", "D": "Д", "d": "д", "E": "Е", "e": "е",
        "F": "Ф", "f": "ф", "G": "Г", "g": "г", "H": "Ҳ", "h": "ҳ", "I": "И", "i": "и",
        "J": "Ж", "j": "ж", "K": "К", "k": "к", "L": "Л", "l": "л", "M": "М", "m": "м",
        "N": "Н", "n": "н", "O": "О", "o": "о", "P": "П", "p": "п", "Q": "Қ", "q": "қ",
        "R": "Р", "r": "р", "S": "С", "s": "с", "T": "Т", "t": "т", "U": "У", "u": "у",
        "V": "В", "v": "в", "X": "Х", "x": "х", "Y": "Й", "y": "й", "Z": "З", "z": "з",
        "'": "ъ"
    }
    
    # First handle multi-char sequences (greedy match)
    for lat, cyr in [
        ("Ya", "Я"), ("ya", "я"), ("Yu", "Ю"), ("yu", "ю"), ("Sh", "Ш"), ("sh", "ш"), ("Ch", "Ч"), ("ch", "ч"),
        ("O'", "Ў"), ("o'", "ў"), ("G'", "Ғ"), ("g'", "ғ"), ("Yo", "Ё"), ("yo", "ё")
    ]:
        text = text.replace(lat, cyr)
    
    # Then single chars
    result = []
    for char in text:
        result.append(mapping.get(char, char))
    
    return "".join(result)


class ObyektivkaGenerator:
    """Generator for professional obyektivka documents."""
    
    def __init__(self, data: Dict[str, Any], lang: str = 'uz_l', is_sample: bool = False):
        """
        Initialize generator with obyektivka data.
        
        Args:
            data: Dictionary containing all obyektivka fields
            lang: Language code ('uz_l' or 'uz_k')
            is_sample: If True, adds 'NAMUNA' watermark (only for Word/PDF logic that supports it)
        """
        self.data = data
        self.lang = lang if lang in LABELS else 'uz_l'
        self.labels = LABELS[self.lang]
        self.is_sample = is_sample
        
        self.fullname = data.get('fullname', '').strip()
        self.birthdate = data.get('birthdate', '').strip()
        self.birthplace = data.get('birthplace', '').strip()
        self.nation = data.get('nation', '').strip()
        self.education = data.get('education', '').strip()
        self.specialty = data.get('specialty', '').strip()
        self.degree = data.get('degree', '').strip()
        self.languages = data.get('languages', '').strip()
        self.awards = data.get('awards', '').strip()
        self.deputy = data.get('deputy', '').strip()
        self.party = data.get('party', '').strip()
        self.graduated = data.get('graduated', '').strip()
        self.scientific_title = data.get('scientific_title', '').strip()
        self.military_rank = data.get('military_rank', '').strip()
        self.photo_data = data.get('photo_data', '').strip()
        
        # Parse JSON fields
        self.work_experience = self._parse_json_field(data.get('work_experience', '[]'))
        self.relatives = self._parse_json_field(data.get('relatives', '[]'))
    
    def _parse_json_field(self, field_value: str) -> List[Dict]:
        """Parse JSON string field to list of dictionaries."""
        if not field_value:
            return []
        try:
            if isinstance(field_value, str):
                return json.loads(field_value)
            elif isinstance(field_value, list):
                return field_value
            return []
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse JSON field: {e}")
            return []
    
    def _decode_photo(self) -> Optional[BytesIO]:
        """Decode base64 photo data or download from URL to BytesIO."""
        if not self.photo_data:
            return None
        try:
            # Check if it is a URL
            if str(self.photo_data).startswith(('http://', 'https://')):
                import requests
                response = requests.get(self.photo_data)
                response.raise_for_status()
                return BytesIO(response.content)

            # Remove data URL prefix if present
            if 'base64,' in self.photo_data:
                self.photo_data = self.photo_data.split('base64,')[1]
            
            photo_bytes = base64.b64decode(self.photo_data)
            return BytesIO(photo_bytes)
        except Exception as e:
            logger.warning(f"Failed to decode/download photo: {e}")
            return None
    
    def _transliterate_if_needed(self, text: str) -> str:
        """Transliterate text to Cyrillic if language is uz_k."""
        if not text:
            return ""
        if self.lang == 'uz_k':
            return latin_to_cyrillic(text)
        return text
    
    def generate_pdf(self) -> BytesIO:
        """
        Generate PDF document with new layout and localization.
        """
        output = BytesIO()
        
        # Document setup
        doc = SimpleDocTemplate(
            output,
            pagesize=A4,
            topMargin=2.0*cm,    # 20mm
            bottomMargin=2.0*cm, # 20mm
            leftMargin=2.5*cm,   # 25mm
            rightMargin=2.5*cm   # 25mm
        )
        
        # Container for PDF elements
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        
        # Update styles to use dynamically determined font (Cyrillic support if available)
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.black,
            fontName=FONT_NAME_REGULAR,
            leading=14
        )
        
        # Title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=14,
            textColor=colors.black,
            spaceAfter=3.5,
            alignment=TA_CENTER,
            fontName=FONT_NAME_BOLD
        )
        
        # Name style
        name_style = ParagraphStyle(
            'CustomName',
            parent=styles['Heading1'],
            fontSize=14,
            textColor=colors.black,
            spaceAfter=14,
            alignment=TA_CENTER,
            fontName=FONT_NAME_BOLD
        )
        
        # Section title style
        section_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.black,
            spaceAfter=10,
            spaceBefore=10,
            alignment=TA_CENTER,
            fontName=FONT_NAME_BOLD
        )
        
        # Add Header
        elements.append(Paragraph(self.labels['title'], title_style))
        elements.append(Paragraph(self.fullname, name_style))
        
        # Custom styles for table content
        label_style = ParagraphStyle(
            'LabelStyle',
            parent=normal_style,
            fontName=FONT_NAME_BOLD,
            fontSize=11,
            leading=14
        )
        value_style = ParagraphStyle(
            'ValueStyle',
            parent=normal_style,
            fontName=FONT_NAME_REGULAR,
            fontSize=12,
            leading=14,
            spaceAfter=6
        )
        
        # Helper to create cell content
        def create_field(label, value):
            return [
                Paragraph(label, label_style),
                Paragraph(value, value_style)
            ]

        # --- DATA PREPARATION ---
        # Rows using localized labels
        r1_c1 = create_field(self.labels['birthdate'], self.birthdate)
        r1_c2 = create_field(self.labels['birthplace'], self.birthplace)
        
        photo_cell = []
        photo_stream = self._decode_photo()
        if photo_stream:
            try:
                img = PILImage.open(photo_stream)
                img_io = BytesIO()
                img.save(img_io, format='PNG')
                img_io.seek(0)
                photo_img = Image(img_io, width=3*cm, height=4*cm)
                photo_cell = [photo_img]
            except Exception:
                photo_cell = []
        
        r2_c1 = create_field(self.labels['nation'], self.nation)
        r2_c2 = create_field(self.labels['party'], self.party)
        
        r3_c1 = create_field(self.labels['education'], self.education)
        r3_c2 = create_field(self.labels['graduated'], self.graduated)
        
        r4_c1 = create_field(self.labels['specialty'], self.specialty)
        
        r5_c1 = create_field(self.labels['degree'], self.degree)
        r5_c2 = create_field(self.labels['scititle'], self.scientific_title)
        
        r6_c1 = create_field(self.labels['langs'], self.languages)
        r6_c2 = create_field(self.labels['military'], self.military_rank)
        
        r7_c1 = create_field(self.labels['awards'], self.awards)
        r8_c1 = create_field(self.labels['deputy'], self.deputy)

        # Build Table Data
        data = [
            [r1_c1, r1_c2, photo_cell],
            [r2_c1, r2_c2, ''],
            [r3_c1, r3_c2, ''],
            [r4_c1, '', ''],
            [r5_c1, r5_c2, ''],
            [r6_c1, r6_c2, ''],
            [r7_c1, '', ''],
            [r8_c1, '', '']
        ]
        
        # Layout style
        tbl_style = [
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('SPAN', (2,0), (2,2)),  # Photo
            ('SPAN', (0,3), (1,3)),  # Specialty
            ('SPAN', (0,6), (2,6)),  # Awards
            ('SPAN', (0,7), (2,7)),  # Deputy
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]
        
        col_widths = [6.5*cm, 6.5*cm, 4*cm]
        main_table = Table(data, colWidths=col_widths)
        main_table.setStyle(TableStyle(tbl_style))
        
        elements.append(main_table)
        elements.append(Spacer(1, 0.5*cm))
        
        # Work experience section
        elements.append(Paragraph(self.labels['work_title'], section_style))
        
        if self.work_experience:
            work_data = []
            for work in self.work_experience:
                year = work.get('year', '').strip()
                # Fix: index.html sends 'position', generator expected 'description'
                description = work.get('position', work.get('description', '')).strip()
                if year or description:
                    year_para = Paragraph(f"<b>{year}</b>", normal_style)
                    desc_para = Paragraph(f"- {description}", normal_style)
                    work_data.append([year_para, desc_para])
            
            if work_data:
                # Use a single column to ensure "1 space" constraint and better wrapping
                # This matches the Word generation logic
                combined_work_data = []
                for work in self.work_experience:
                    year = work.get('year', '').strip()
                    description = work.get('position', work.get('description', '')).strip()
                    if year or description:
                        # Combine year and description with a single space and dash
                        text = ""
                        if year:
                            text += f"<b>{year}</b> - "
                        text += description
                        combined_work_data.append([Paragraph(text, normal_style)])
                
                work_table = Table(combined_work_data, colWidths=[17*cm])
                work_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                elements.append(work_table)
        else:
            elements.append(Paragraph(self.labels['work_empty'], normal_style))
        
        # Page break for relatives
        elements.append(PageBreak())
        
        # Relatives section
        rel_title_text = f"{self.fullname}{self.labels['rel_title_suffix']}<br/>{self.labels['rel_subtitle']}"
        elements.append(Paragraph(rel_title_text, section_style))
        elements.append(Spacer(1, 0.3*cm))
        
        # Relatives table
        rel_data = []
        
        # Header row
        headers = [
            self.labels['rel_col1'],
            self.labels['rel_col2'],
            self.labels['rel_col3'],
            self.labels['rel_col4'],
            self.labels['rel_col5']
        ]
        header_row = [Paragraph(f"<b>{h}</b>", normal_style) for h in headers]
        rel_data.append(header_row)
        
        # Data rows
        if self.relatives:
            for relative in self.relatives:
                rel_type = self._transliterate_if_needed(relative.get('type', ''))
                row = [
                    Paragraph(f"<b>{rel_type}</b>", normal_style),
                    Paragraph(self._transliterate_if_needed(relative.get('name', '')), normal_style),
                    Paragraph(self._transliterate_if_needed(relative.get('birth', '')), normal_style),
                    Paragraph(self._transliterate_if_needed(relative.get('job', '')), normal_style),
                    Paragraph(self._transliterate_if_needed(relative.get('addr', '')), normal_style),
                ]
                rel_data.append(row)
        else:
            empty_cell = Paragraph(self.labels['rel_empty'], normal_style)
            rel_data.append([empty_cell, '', '', '', ''])
        
        rel_table = Table(rel_data, colWidths=[3*cm, 4*cm, 3.5*cm, 3.5*cm, 3*cm])
        rel_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.96, 0.96, 0.96)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), FONT_NAME_BOLD),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        elements.append(rel_table)
        
        # Build PDF with watermark if needed
        if self.is_sample:
            # Create watermark function with multiple boxes
            def add_watermark(canvas, doc):
                canvas.saveState()
                
                # Draw multiple watermark boxes across the page
                watermark_text = "@Obyektivkaa_bot"
                
                # Settings
                box_width = 5*cm
                box_height = 1.5*cm
                font_size = 16
                
                # Create diagonal pattern
                positions = [
                    (3*cm, 25*cm),
                    (10*cm, 22*cm),
                    (3*cm, 18*cm),
                    (10*cm, 15*cm),
                    (3*cm, 11*cm),
                    (10*cm, 8*cm),
                    (3*cm, 4*cm),
                ]
                
                for x, y in positions:
                    # Draw semi-transparent black rectangle
                    canvas.setFillColorRGB(0, 0, 0, 0.6)  # Qora, 60% shaffof
                    canvas.rect(x, y, box_width, box_height, fill=1, stroke=0)
                    
                    # Draw white text inside
                    canvas.setFillColorRGB(1, 1, 1, 1)  # Oq rang
                    canvas.setFont('Times-Bold', font_size)
                    # Center text in box
                    text_x = x + box_width / 2
                    text_y = y + box_height / 2 - font_size / 3
                    canvas.drawCentredString(text_x, text_y, watermark_text)
                
                canvas.restoreState()
            
            doc.build(elements, onFirstPage=add_watermark, onLaterPages=add_watermark)
        else:
            doc.build(elements)
        
        output.seek(0)
        return output

    def generate_word(self) -> BytesIO:
        """
        Generate Word document with new layout and localization.
        """
        doc = Document()
        
        # Margins (Narrower)
        sections = doc.sections
        for section in sections:
            section.top_margin = Cm(1.5)
            section.bottom_margin = Cm(1.5)
            section.left_margin = Cm(2)
            section.right_margin = Cm(1.5)
        
        # Default Font
        style = doc.styles['Normal']
        font = style.font
        font.name = 'Times New Roman'
        font.size = Pt(12)

        # SAMPLE WATERMARK (Text Header)
        if self.is_sample:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(self.labels.get('sample_watermark', 'NAMUNA (TASDIQLANMAGAN)'))
            run.bold = True
            run.font.size = Pt(24)
            run.font.color.rgb = RGBColor(255, 0, 0)
        
        # Helper to add bold label + value
        def add_item(paragraph, label, value):
            run = paragraph.add_run(f"{label}\n")
            run.bold = True
            paragraph.add_run(f"{value}")
            paragraph.paragraph_format.space_after = Pt(6)

        # Title
        title = doc.add_paragraph(self.labels['title'])
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title.runs[0].bold = True
        title.runs[0].font.size = Pt(14)
        
        name_para = doc.add_paragraph()
        name_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if self.fullname:
            run = name_para.add_run(self.fullname)
            run.bold = True
            run.font.size = Pt(14)
        name_para.paragraph_format.space_after = Pt(12)
        
        # Main Table (3 columns)
        table = doc.add_table(rows=0, cols=3)
        table.autofit = False
        table.allow_autofit = False
        table.columns[0].width = Cm(7)
        table.columns[1].width = Cm(7)
        table.columns[2].width = Cm(3.5)
        
        # Row 1
        row = table.add_row()
        add_item(row.cells[0].paragraphs[0], self.labels['birthdate'], self.birthdate)
        add_item(row.cells[1].paragraphs[0], self.labels['birthplace'], self.birthplace)
        
        # Row 2
        row2 = table.add_row()
        add_item(row2.cells[0].paragraphs[0], self.labels['nation'], self.nation)
        add_item(row2.cells[1].paragraphs[0], self.labels['party'], self.party)
        
        # Row 3
        row3 = table.add_row()
        add_item(row3.cells[0].paragraphs[0], self.labels['education'], self.education)
        add_item(row3.cells[1].paragraphs[0], self.labels['graduated'], self.graduated)
        
        # Merge Photo Cells (Row 0, Col 2  TO  Row 2, Col 2)
        photo_cell = table.cell(0, 2)
        photo_cell.merge(table.cell(2, 2))
        
        photo_stream = self._decode_photo()
        if photo_stream:
            try:
                p = photo_cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.add_run()
                run.add_picture(photo_stream, width=Cm(3), height=Cm(4))
            except Exception:
                pass
        
        # Row 4 (Specialty)
        row4 = table.add_row()
        add_item(row4.cells[0].paragraphs[0], self.labels['specialty'], self.specialty)
        row4.cells[0].merge(row4.cells[1])
        
        # Row 5
        row5 = table.add_row()
        add_item(row5.cells[0].paragraphs[0], self.labels['degree'], self.degree)
        add_item(row5.cells[1].paragraphs[0], self.labels['scititle'], self.scientific_title)
        
        # Row 6
        row6 = table.add_row()
        add_item(row6.cells[0].paragraphs[0], self.labels['langs'], self.languages)
        add_item(row6.cells[1].paragraphs[0], self.labels['military'], self.military_rank)
        
        # Row 7 (Awards)
        row7 = table.add_row()
        add_item(row7.cells[0].paragraphs[0], self.labels['awards'], self.awards)
        row7.cells[0].merge(row7.cells[2])
        
        # Row 8 (Deputy)
        row8 = table.add_row()
        add_item(row8.cells[0].paragraphs[0], self.labels['deputy'], self.deputy)
        row8.cells[0].merge(row8.cells[2])
        
        doc.add_paragraph()
        
        # Work Experience
        work_title = doc.add_paragraph(self.labels['work_title'])
        work_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        work_title.runs[0].bold = True
        
        if self.work_experience:
            # Use 1-column table to ensure "1 space" constraint and proper wrapping
            work_table = doc.add_table(rows=0, cols=1)
            work_table.autofit = False
            work_table.allow_autofit = False
            work_table.columns[0].width = Cm(17.5)  # Full width
            
            for work in self.work_experience:
                year = work.get('year', '').strip()
                description = work.get('position', work.get('description', '')).strip()
                if year or description:
                    row = work_table.add_row()
                    cell = row.cells[0]
                    p = cell.paragraphs[0]
                    
                    # Exact format: "2019-2024 йй. - Havs..." (Single space, bold year)
                    if year:
                        r_year = p.add_run(year)
                        r_year.bold = True
                        p.add_run(" - ")
                    
                    p.add_run(description)
                    p.paragraph_format.space_after = Pt(2)

        doc.add_page_break()
        
        # Relatives
        rel_title = doc.add_paragraph(f"{self.fullname}{self.labels['rel_title_suffix']}")
        rel_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rel_title.runs[0].bold = True
        
        rel_subtitle = doc.add_paragraph(self.labels['rel_subtitle'])
        rel_subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rel_subtitle.runs[0].bold = True
        
        # Relatives Table
        headers = [
            self.labels['rel_col1'],
            self.labels['rel_col2'],
            self.labels['rel_col3'],
            self.labels['rel_col4'],
            self.labels['rel_col5']
        ]
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
                
                # Fill data
                c0 = row.cells[0]
                c0.text = self._transliterate_if_needed(relative.get('type', ''))
                # User request: Bold first column (Qarindoshligi)
                if c0.paragraphs:
                    if c0.paragraphs[0].runs:
                        c0.paragraphs[0].runs[0].bold = True
                    else:
                        # Sometimes text assign doesn't create runs immediately visible like this? 
                        # Force bold on the text just assigned
                        c0.paragraphs[0].runs[0].bold = True

                row.cells[1].text = self._transliterate_if_needed(relative.get('name', ''))
                row.cells[2].text = self._transliterate_if_needed(relative.get('birth', ''))
                row.cells[3].text = self._transliterate_if_needed(relative.get('job', ''))
                row.cells[4].text = self._transliterate_if_needed(relative.get('addr', ''))
                
                # Format cells
                for i, cell in enumerate(row.cells):
                    # User request: Center all content
                    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                    
                    for paragraph in cell.paragraphs:
                        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        
                        # First column bolding (Ensure it persists)
                        if i == 0:
                            for run in paragraph.runs:
                                run.bold = True
                        
                        for run in paragraph.runs:
                            run.font.size = Pt(11)
                            run.font.name = 'Times New Roman'
        else:
            row_cells = rel_table.add_row().cells
            # Merge all cells
            merged_cell = row_cells[0].merge(row_cells[4])
            merged_cell.text = self.labels['rel_empty']
            for paragraph in merged_cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
                    run.font.size = Pt(11)
                    run.font.name = 'Times New Roman'
        
        # Save to buffer
        output = BytesIO()
        doc.save(output)
        output.seek(0)
        return output


def generate_obyektivka_word(data: Dict[str, Any], lang: str = 'uz_l', is_sample: bool = False) -> BytesIO:
    """
    Generate Word document for obyektivka.
    
    Args:
        data: Dictionary containing obyektivka data
        lang: Language code
        is_sample: If True, adds 'NAMUNA' watermark
    
    Returns:
        BytesIO containing the Word document
    """
    generator = ObyektivkaGenerator(data, lang=lang, is_sample=is_sample)
    return generator.generate_word()


def generate_obyektivka_pdf(data: Dict[str, Any], lang: str = 'uz_l', is_sample: bool = False) -> BytesIO:
    """
    Generate PDF document for obyektivka.
    
    Args:
        data: Dictionary containing obyektivka data
        lang: Language code
        is_sample: If True, adds 'NAMUNA' watermark
    
    Returns:
        BytesIO containing the PDF document
    """
    generator = ObyektivkaGenerator(data, lang=lang, is_sample=is_sample)
    return generator.generate_pdf()


# ─────────────────────────────────────────────────────────────────────────────
# Legacy compatibility shims
# 
# Older parts of the codebase (e.g. bot.handlers.webapp_data, api_webhook)
# import the following helpers from bot.services.doc_generator:
#   - generate_obyektivka_docx
#   - generate_cv_docx
#   - convert_to_pdf_safe
#
# The actual, template-accurate DOCX generation logic now lives in
# bot.keyboards.doc_generator, so we re-export thin wrappers here to
# avoid breaking those imports.
# ─────────────────────────────────────────────────────────────────────────────

def generate_obyektivka_docx(data: Dict[str, Any], photo_path: Optional[str] = None, output_dir: str = "temp") -> str:
    """
    Backwards-compatible wrapper that forwards to
    bot.keyboards.doc_generator.generate_obyektivka_docx.

    Note: current implementation in bot.keyboards.doc_generator does not
    accept/consume photo_path directly; photo handling is done upstream
    (e.g. via data fields or dedicated generators), so we ignore it here.
    """
    from bot.keyboards.doc_generator import generate_obyektivka_docx as _legacy_generate_obyektivka_docx

    os.makedirs(output_dir, exist_ok=True)
    return _legacy_generate_obyektivka_docx(data, output_dir=output_dir)


def generate_cv_docx(data: Dict[str, Any], output_dir: str = "temp") -> str:
    """
    Backwards-compatible wrapper delegating to
    bot.keyboards.doc_generator.generate_cv_docx.
    """
    from bot.keyboards.doc_generator import generate_cv_docx as _legacy_generate_cv_docx

    os.makedirs(output_dir, exist_ok=True)
    return _legacy_generate_cv_docx(data, output_dir=output_dir)


def convert_to_pdf_safe(docx_path: str, output_dir: str = "temp") -> Optional[str]:
    """
    Backwards-compatible wrapper around
    bot.keyboards.doc_generator.convert_to_pdf_safe.
    """
    from bot.keyboards.doc_generator import convert_to_pdf_safe as _legacy_convert_to_pdf_safe

    os.makedirs(output_dir, exist_ok=True)
    return _legacy_convert_to_pdf_safe(docx_path, output_dir=output_dir)

