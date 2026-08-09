import sys
import zipfile
from pathlib import Path

from lxml import etree

from features.obyektivka.docx_template import generate_obyektivka_docx
from features.obyektivka.docx_typography import W, _is_bold_run, run_has_underline

sys.stdout.reconfigure(encoding="utf-8")
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
for para in root.findall(f".//{W}body/{W}p"):
    texts = []
    for r in para.findall(f".//{W}r"):
        t = "".join(x.text or "" for x in r.findall(f".//{W}t"))
        if "25.10.1960" in t or "O'zbek" in t:
            rpr = r.find(f"{W}rPr")
            xml = etree.tostring(rpr, encoding="unicode") if rpr is not None else "none"
            print("RUN", t, "bold=", _is_bold_run(r), "ul=", run_has_underline(r))
            print(xml)
