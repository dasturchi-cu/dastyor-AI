import re
import zipfile

xml = zipfile.ZipFile("temp/ref_converted.docx").read("word/document.xml").decode("utf-8")

for m in re.finditer(r"<w:u[^>]*/>", xml):
    start = max(0, m.start() - 200)
    snippet = xml[start : m.end() + 80]
    text = re.search(r"<w:t[^>]*>([^<]*)</w:t>", snippet)
    print("U:", m.group(), "near:", text.group(1)[:40] if text else "?")

for m in re.finditer(r"<w:highlight[^>]*/>", xml):
    start = max(0, m.start() - 150)
    snippet = xml[start : m.end() + 100]
    text = re.search(r"<w:t[^>]*>([^<]*)</w:t>", snippet)
    print("HL:", m.group(), "near:", text.group(1)[:50] if text else "?")

# tbl borders
tbl = re.search(r"<w:tbl>.*?</w:tbl>", xml, re.DOTALL)
if tbl:
    borders = re.findall(r"<w:tblBorders>.*?</w:tblBorders>", tbl.group(), re.DOTALL)
    print("tblBorders found", len(borders))
    if borders:
        print(borders[0][:500])
