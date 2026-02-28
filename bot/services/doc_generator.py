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


def generate_cv_docx(data: dict, output_dir: str = "temp") -> str:
    """Generate a modern CV DOCX file"""
    os.makedirs(output_dir, exist_ok=True)
    filename = f"cv_{data.get('name', 'unknown').replace(' ', '_')}.docx"
    filepath = os.path.join(output_dir, filename)
    
    document = Document()
    
    title = document.add_heading("CV / REZYUME", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Header Info
    p = document.add_paragraph()
    r = p.add_run(f"{data.get('name', 'N/A')}\n")
    r.bold = True
    r.font.size = Pt(16)
    p.add_run(f"{data.get('spec', 'Mutaxassis')}\n")
    
    p.add_run(f"Tug'ilgan sana / joy: {data.get('birth', '')} {data.get('place', '')}\n")
    p.add_run(f"Millati: {data.get('nation', '')}\n")
    p.add_run(f"Manzil: {data.get('addr', '')}")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    document.add_heading("🎯 TA'LIM VA KO'NIKMALAR", level=2)
    document.add_paragraph(f"Ma'lumoti: {data.get('edu', '')}")
    document.add_paragraph(f"Tamomlagan joylar: {data.get('grad', '')}")
    document.add_paragraph(f"Tillar: {data.get('langs', '')}")
    document.add_paragraph(f"Maxsus ko'nikmalar: {data.get('skills', '')}")
    
    document.add_heading("💼 ISH TAJRIBASI", level=2)
    works = data.get('works', [])
    if isinstance(works, list) and works:
        for w in works:
            p = document.add_paragraph()
            p.add_run(f"{w.get('f', '')} – {w.get('t', '')}\n").bold = True
            p.add_run(f"{w.get('d', '')}")
    else:
        document.add_paragraph("Kiritilmagan.")
        
    document.add_heading("👨‍👩‍👧‍👦 OILA A'ZOLARI", level=2)
    rels = data.get('rels', [])
    if isinstance(rels, list) and rels:
        for r in rels:
            document.add_paragraph(f"{r.get('type', '')}: {r.get('name', '')} ({r.get('birth', '')}), Manzil: {r.get('addr', '')}, Ish joyi: {r.get('job', '')}")
            
    document.save(filepath)
    return filepath


def convert_to_pdf_safe(docx_path: str, output_dir: str = "temp") -> str:
    """Safe DOCX to PDF conversion (cross-platform fallback)"""
    pdf_path = docx_path.replace(".docx", ".pdf")
    
    # 1. Try Windows native docx2pdf
    try:
        from docx2pdf import convert
        convert(docx_path, pdf_path)
        if os.path.exists(pdf_path): return pdf_path
    except Exception as e:
        print(f"docx2pdf faile: {e}")
        
    # 2. Try Linux LibreOffice fallback
    try:
        import subprocess
        subprocess.run(['libreoffice', '--headless', '--convert-to', 'pdf', docx_path, '--outdir', output_dir], check=True)
        if os.path.exists(pdf_path): return pdf_path
    except Exception as e:
        print(f"LibreOffice fail: {e}")
        
    return None
