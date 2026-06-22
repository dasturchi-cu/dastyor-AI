import zipfile
from pathlib import Path

from lxml import etree

from features.obyektivka.docx_template import generate_obyektivka_docx

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"
VAL = f"{{{W_NS}}}val"


def is_bold(r):
    rpr = r.find(f"{W}rPr")
    if rpr is None:
        return False
    b = rpr.find(f"{W}b")
    return b is not None and b.get(VAL) != "0"


def cell_text(tc):
    return "".join(t.text or "" for t in tc.findall(f".//{W}t")).strip()


out = Path("temp/test_rel_bold.docx")
path = generate_obyektivka_docx(
    {
        "fullname": "Test User",
        "lang": "uz_lat",
        "birthdate": "01.01.1990",
        "relatives": [
            {
                "degree": "Otasi",
                "fullname": "tasd",
                "birth_year_place": "12.06.2000",
                "work_place": "Tadbirkor",
                "address": "dasdas",
            }
        ],
    },
    output_filepath=str(out),
)
root = etree.fromstring(zipfile.ZipFile(path).read("word/document.xml"))

for tbl in root.findall(f".//{W}tbl"):
    rows = tbl.findall(f"{W}tr")
    lines = []
    for ri, tr in enumerate(rows):
        cells = []
        for tc in tr.findall(f"{W}tc"):
            t = cell_text(tc)
            bold = any(is_bold(r) for r in tc.findall(f".//{W}r") if (r.find(f".//{W}t") is not None))
            cells.append(f"{t[:30]!r}(b={bold})")
        lines.append(f"row {ri}: {cells}")
Path("temp/rel_table_debug.txt").write_text("\n".join(lines), encoding="utf-8")
