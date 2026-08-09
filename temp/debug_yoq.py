import re
import zipfile
from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
xml = zipfile.ZipFile("temp/layout_check.docx").read("word/document.xml")
root = etree.fromstring(xml)
for p in root.findall(f".//{W}p"):
    t = "".join(x.text or "" for x in p.findall(f".//{W}t"))
    if "yo" in t and "q" in t and len(t) < 30:
        print(repr(t), [hex(ord(c)) for c in t])
