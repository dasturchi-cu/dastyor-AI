from pathlib import Path
from features.obyektivka.docx_template import generate_obyektivka_docx
from lxml import etree
import zipfile

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
VAL = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val"
out = Path("temp/paid_check.docx")
generate_obyektivka_docx(
    {"fullname": "Test", "lang": "uz_lat", "work_experience": [], "relatives": []},
    output_filepath=str(out),
)
root = etree.fromstring(zipfile.ZipFile(out).read("word/document.xml"))
lines = []
for i, tbl in enumerate(root.findall(f".//{W}tbl")):
    tbl_pr = tbl.find(f"{W}tblPr")
    jc = tbl_pr.find(f"{W}jc") if tbl_pr is not None else None
    tw = tbl_pr.find(f"{W}tblW") if tbl_pr is not None else None
    ind = tbl_pr.find(f"{W}tblInd") if tbl_pr is not None else None
    lines.append(
        f"tbl{i} jc={jc.get(VAL) if jc is not None else None} "
        f"tw_w={tw.get(f'{W}w') if tw is not None else None} ind={ind is not None}"
    )
# page breaks
pb = root.findall(f".//{W}br")
lines.append(f"page_breaks={sum(1 for b in pb if b.get(VAL) == 'page')}")
Path("temp/paid_check.txt").write_text("\n".join(lines), encoding="utf-8")
print("ok", len(lines))
