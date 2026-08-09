import sys
from docx import Document

sys.stdout.reconfigure(encoding="utf-8")

doc = Document("temp/ref_converted.docx")
for name in ["Heading 6", "Normal", "Heading 2", "Heading 1"]:
    try:
        s = doc.styles[name]
        pf = s.paragraph_format
        print(name, "align", s.paragraph_format.alignment if hasattr(s, 'paragraph_format') else None)
        print("  font", s.font.name, s.font.size, "bold", s.font.bold)
    except KeyError:
        print(name, "missing")

p0 = doc.paragraphs[0]
print("P0 style", p0.style.name, "effective align", p0.alignment)
