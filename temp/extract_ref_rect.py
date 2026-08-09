import re
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")

doc = zipfile.ZipFile("temp/ref_converted.docx").read("word/document.xml").decode("utf-8")

for m in re.finditer(r"<w:pict>.*?</w:pict>", doc, re.S):
    block = m.group(0)
    if "v:rect" in block:
        print("RECT PICT:")
        print(block)
        print("---")

rects = re.findall(r'v:rect[^>]+style="([^"]+)"', doc)
print("rect count", len(rects))
for r in rects:
    print(r)
