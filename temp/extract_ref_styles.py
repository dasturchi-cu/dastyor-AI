import re
import sys
import zipfile
from xml.etree import ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")

z = zipfile.ZipFile("temp/ref_converted.docx")
styles = z.read("word/styles.xml")
ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
root = ET.fromstring(styles)
for st in root.findall(".//w:style", ns):
    sid = st.get(f"{{{ns['w']}}}styleId")
    if sid in ("Normal", "Heading6", "Heading2", "a"):
        rf = st.find(".//w:rFonts", ns)
        print(sid, dict(rf.attrib) if rf is not None else None)

doc = z.read("word/document.xml").decode()
# sample rFonts from body text runs
for m in re.finditer(r"<w:rFonts[^/]*/>", doc):
    print(m.group(0))
