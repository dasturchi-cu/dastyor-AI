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


def txt(r):
    return "".join(t.text or "" for t in r.findall(f".//{W}t")).strip()


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

needles = {"yo'q", "tasd", "12.06.2000", "Tadbirkor", "dasdas", "Otasi"}
for r in root.findall(f".//{W}r"):
    t = txt(r)
    if t in needles:
        print(f"{t!r} bold={is_bold(r)}")
