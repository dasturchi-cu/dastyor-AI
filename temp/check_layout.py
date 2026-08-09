"""Dump layout info from generated obyektivka docx."""
from pathlib import Path

from features.obyektivka.docx_template import generate_obyektivka_docx

out = Path("temp/layout_check.docx")
generate_obyektivka_docx(
    {
        "fullname": "Test User",
        "lang": "uz_lat",
        "current_job": "Tadbirkor",
        "current_job_year": "2024",
        "work_experience": [
            {"year": "1986-1987", "position": "tst"},
            {"year": "1986-1988", "position": "etesd"},
        ],
        "relatives": [{"degree": "Otasi", "fullname": "tasd", "birth_year_place": "12.06.2000", "work_place": "Tadbirkor", "address": "dasdas"}],
    },
    output_filepath=str(out),
)
print("written", out)

import re
import zipfile

xml = zipfile.ZipFile(out).read("word/document.xml").decode("utf-8")
# fish / current job area
for needle in ["Test User", "2024", "Tadbirkor", "1986-1987", "tasd", "yo'q"]:
    i = xml.find(needle)
    if i < 0:
        print("missing", needle)
        continue
    ps = xml.rfind("<w:p", 0, i)
    pe = xml.find("</w:p>", i) + 6
    p = xml[ps:pe]
    text = re.sub(r"<[^>]+>", "", p)
    u = "u w:val" in p and 'w:val="none"' not in p.split("u w:val")[1][:20] if "u w:val" in p else False
    sb = re.search(r'w:before="([0-9]+)"', p)
    sa = re.search(r'w:after="([0-9]+)"', p)
    line = re.search(r'w:line="([0-9]+)"', p)
    print("---", needle, repr(text[:80]))
    print(" underline", "u" in p and 'w:val="single"' in p, "before", sb and sb.group(1), "after", sa and sa.group(1), "line", line and line.group(1))
