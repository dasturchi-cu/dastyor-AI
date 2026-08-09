import re
import zipfile
from docx import Document

xml = zipfile.ZipFile("temp/ref_converted.docx").read("word/document.xml").decode("utf-8")
m = re.search(r"<w:sectPr.*?</w:sectPr>", xml, re.DOTALL)
if m:
    s = m.group(0)
    for tag in ("top", "right", "bottom", "left"):
        t = re.search(rf"w:{tag} w:w=\"(\d+)\"", s)
        if t:
            tw = int(t.group(1))
            print(tag, "twips", tw, "cm", round(tw / 567, 2))
    pg = re.search(r'w:pgSz w:w="(\d+)" w:h="(\d+)"', s)
    if pg:
        print("page cm", round(int(pg.group(1)) / 567, 2), "x", round(int(pg.group(2)) / 567, 2))

v = re.search(r"v:rect[^>]*style=\"([^\"]+)\"", xml)
if v:
    print("vml", v.group(1))

d = Document("temp/ref_converted.docx")
sec = d.sections[0]
print("docx margins mm", sec.left_margin.mm, sec.right_margin.mm, sec.top_margin.mm, sec.bottom_margin.mm)
