import re
import sys
import zipfile
from docx import Document

sys.stdout.reconfigure(encoding="utf-8")

doc = Document("temp/ref_converted.docx")
for i in range(4):
    p = doc.paragraphs[i]
    picts = p._p.xpath(".//w:pict")
    rects = p._p.xpath(".//*[local-name()='rect']")
    print(f"p{i} picts={len(picts)} rects={len(rects)} text={repr(p.text[:60])}")
    for j, pict in enumerate(picts):
        xml = pict.xml[:300]
        has_1030 = "_x0000_s1030" in pict.xml
        has_rect = "rect" in pict.xml
        print(f"  pict{j} s1030={has_1030} rect={has_rect} snippet={xml[:150]}")
