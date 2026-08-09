import sys
import zipfile
from pathlib import Path

from lxml import etree

from features.obyektivka.docx_template import generate_obyektivka_docx

sys.stdout.reconfigure(encoding="utf-8")
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
out = Path("temp/inspect_typo.docx")
generate_obyektivka_docx(
    {
        "fullname": "Test User",
        "lang": "uz_cyr",
        "birthdate": "25.10.1960",
        "nation": "O'zbek",
        "work_experience": [],
        "relatives": [],
    },
    output_filepath=str(out),
)
root = etree.fromstring(zipfile.ZipFile(out).read("word/document.xml"))
for i, para in enumerate(root.findall(f".//{W}body/{W}p")[:35]):
    parts = []
    for r in para.findall(f".//{W}r"):
        t = "".join(x.text or "" for x in r.findall(f".//{W}t"))
        if not t.strip():
            continue
        rpr = r.find(f"{W}rPr")
        b = rpr is not None and rpr.find(f"{W}b") is not None
        u = rpr is not None and rpr.find(f"{W}u") is not None
        sz = rpr.find(f"{W}sz") if rpr is not None else None
        pt = int(sz.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val")) / 2 if sz is not None else "?"
        tag = "B" if b else "n"
        if u:
            tag += "U"
        parts.append(f"[{tag},{pt}pt]{t[:50]}")
    if parts:
        print(i, " | ".join(parts))
