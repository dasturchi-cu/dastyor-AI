import re
import zipfile
from lxml import etree

from features.obyektivka.docx_layout import _dedupe_cell_none_values, _paragraph_text
from features.obyektivka.docx_typography import render_document_xml
from features.obyektivka.placeholders import build_placeholder_context

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
ctx = build_placeholder_context(
    {
        "fullname": "Test User",
        "lang": "uz_lat",
        "current_job": "Tadbirkor",
        "current_job_year": "2024",
        "relatives": [
            {
                "degree": "Otasi",
                "fullname": "tasd",
                "birth_year_place": "12.06.2000",
                "work_place": "Tadbirkor",
                "address": "dasdas",
            }
        ],
    }
)
xml = zipfile.ZipFile("templates/obyektivka_master.docx").read("word/document.xml")
out = render_document_xml(xml, ctx)
root = etree.fromstring(out)
before = sum(1 for p in root.findall(f".//{W}p") if _paragraph_text(p) == "yo'qyo'q")
print("before yoqyoq paragraphs", before)
_dedupe_cell_none_values(root)
after = sum(1 for p in root.findall(f".//{W}p") if _paragraph_text(p) == "yo'qyo'q")
print("after yoqyoq paragraphs", after)
