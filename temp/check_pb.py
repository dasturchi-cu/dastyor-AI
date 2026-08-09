import re
import zipfile
from pathlib import Path

from features.obyektivka.docx_template import generate_obyektivka_docx

p = Path("temp/paid_check2.docx")
generate_obyektivka_docx(
    {"fullname": "Test", "lang": "uz_lat", "work_experience": [], "relatives": []},
    output_filepath=str(p),
)
xml = zipfile.ZipFile(p).read("word/document.xml").decode("utf-8")
print("page_breaks", len(re.findall(r'w:type="page"', xml)))
print("jc center", xml.count('w:val="center"'))
for m in re.finditer(r"<w:tblW[^>]*/>", xml):
    print("tblW", m.group(0))
