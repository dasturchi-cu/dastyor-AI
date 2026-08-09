import re
import zipfile
from lxml import etree

from features.obyektivka.docx_layout import _paragraph_text
from features.obyektivka.docx_typography import render_document_xml
from features.obyektivka.placeholders import build_placeholder_context

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
none_pat = re.compile(r"^(yo'q|йўқ)+$", re.IGNORECASE)
ctx = build_placeholder_context({"fullname": "T", "lang": "uz_lat", "party": "yo'q"})
xml = zipfile.ZipFile("templates/obyektivka_master.docx").read("word/document.xml")
root = etree.fromstring(render_document_xml(xml, ctx))
for p in root.findall(f".//{W}p"):
    t = _paragraph_text(p)
    if "yo" in t and len(t) < 12:
        print(repr(t), "match", bool(none_pat.match(t.replace(" ", ""))))
