from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import os

def generate_obyektivka_docx(data: dict, output_dir: str = "temp") -> str:
    """
    Generate Obyektivka DOCX file based on extracted data.
    """
    os.makedirs(output_dir, exist_ok=True)
    filename = f"obyektivka_{data.get('fullname', 'unknown').replace(' ', '_')}.docx"
    filepath = os.path.join(output_dir, filename)
    
    document = Document()
    
    # Title
    title = document.add_heading("MA'LUMOTNOMA", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Fullname
    p = document.add_paragraph()
    runner = p.add_run(data.get('fullname', ''))
    runner.bold = True
    runner.font.size = Pt(14)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Basic Info Table
    table = document.add_table(rows=0, cols=2)
    table.style = 'Table Grid'
    
    def add_row(label, value):
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = str(value)
        
    add_row("Tug'ilgan yili:", data.get('birthdate', ''))
    add_row("Tug'ilgan joyi:", data.get('birthplace', ''))
    add_row("Millati:", data.get('nation', ''))
    add_row("Partiyaviyligi:", data.get('party', ''))
    add_row("Ma'lumoti:", data.get('education', ''))
    add_row("Tamomlagan:", data.get('graduated', ''))
    add_row("Mutaxassisligi:", data.get('specialty', ''))
    add_row("Ilmiy darajasi:", data.get('degree', ''))
    add_row("Ilmiy unvoni:", data.get('scientific_title', ''))
    add_row("Qaysi chet tillarini biladi:", data.get('languages', ''))
    add_row("Harbiy unvoni:", data.get('military_rank', ''))
    add_row("Davlat mukofotlari:", data.get('awards', ''))
    add_row("Deputatligi:", data.get('deputy', ''))
    
    document.add_paragraph()  # Spacer
    
    # Work Experience
    document.add_heading("MEHNAT FAOLIYATI", level=2)
    
    work_table = document.add_table(rows=1, cols=2)
    work_table.style = 'Table Grid'
    hdr_cells = work_table.rows[0].cells
    hdr_cells[0].text = 'Yillar'
    hdr_cells[1].text = 'Ish joyi va lavozimi'
    
    works = data.get('work_experience', [])
    if isinstance(works, list):
        for work in works:
            row_cells = work_table.add_row().cells
            row_cells[0].text = work.get('year', '')
            row_cells[1].text = work.get('position', '')
            
    document.save(filepath)
    return filepath
