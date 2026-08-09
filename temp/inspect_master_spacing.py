import re
import zipfile
from pathlib import Path

xml = zipfile.ZipFile("templates/obyektivka_master.docx").read("word/document.xml").decode("utf-8")
keys = [
    "{{fish}}",
    "{{hozirgi_yil}}",
    "{{hozirgi_ish}}",
    "{{mehnat_faoliyati}}",
    "MEHNAT",
    "MEҲNAT",
]
for k in keys:
    i = xml.find(k)
    if i < 0:
        continue
    para_start = xml.rfind("<w:p", 0, i)
    para_end = xml.find("</w:p>", i) + 6
    p = xml[para_start:para_end]
    text = re.sub(r"<[^>]+>", "", p)
    sb = re.search(r'w:before="([0-9]+)"', p)
    sa = re.search(r'w:after="([0-9]+)"', p)
    line = re.search(r'w:line="([0-9]+)"', p)
    print("KEY", k)
    print(" TEXT", repr(text[:120]))
    print(
        " before",
        sb.group(1) if sb else "-",
        "after",
        sa.group(1) if sa else "-",
        "line",
        line.group(1) if line else "-",
    )
    print()

# relatives table rows
tbl_start = xml.find("<w:tbl")
tbl_end = xml.find("</w:tbl>", tbl_start) + 8
tbl = xml[tbl_start:tbl_end]
rows = re.findall(r"<w:tr[\s\S]*?</w:tr>", tbl)
print("TABLE ROWS", len(rows))
for idx, row in enumerate(rows[:4]):
    text = re.sub(r"<[^>]+>", "", row)[:90]
    trh = re.search(r"<w:trHeight[^>]*w:val=\"([0-9]+)\"", row)
    print(idx, repr(text), "trHeight", trh.group(1) if trh else "-")
