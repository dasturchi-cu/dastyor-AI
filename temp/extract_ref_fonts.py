import json
import sys
import zipfile
from collections import Counter

from docx import Document

sys.stdout.reconfigure(encoding="utf-8")

doc = Document("temp/ref_converted.docx")
fonts = Counter()
for p in doc.paragraphs:
    for r in p.runs:
        if r.font.name:
            fonts[r.font.name] += 1
        # check XML rFonts
        rfonts = r._r.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rPr")
        if rfonts is not None:
            rf = rfonts.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rFonts")
            if rf is not None:
                fonts[rf.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}ascii") or rf.get("w:ascii") or ""] += 1

print("run fonts", fonts.most_common(10))

# check rels for images
rels = zipfile.ZipFile("temp/ref_converted.docx").read("word/_rels/document.xml.rels").decode()
print("image rels:", [line for line in rels.splitlines() if "image" in line.lower()][:5])
