import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")

ref = Path("temp/ref_converted.docx")
z = zipfile.ZipFile(ref)
doc = z.read("word/document.xml").decode("utf-8")

idx = doc.find("w:pict")
if idx >= 0:
    print("PICT SNIPPET:")
    print(doc[max(0, idx - 200) : idx + 2800])
else:
    for tag in ("wp:anchor", "wp:inline", "v:shape", "v:imagedata", "w:pict"):
        print(tag, doc.count(tag))

styles = z.read("word/styles.xml").decode("utf-8")
fonts = set(re.findall(r'w:ascii="([^"]+)"', styles))
print("style fonts:", sorted(f for f in fonts if "Times" in f or "Uzb" in f))

root = ET.fromstring(z.read("word/document.xml"))
ns = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "v": "urn:schemas-microsoft-com:vml",
    "o": "urn:schemas-microsoft-com:office:office",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
for i, p in enumerate(root.findall(".//w:p", ns)[:8]):
    pict = p.find(".//w:pict", ns)
    if pict is not None:
        print("para", i, "has pict")
        ET.indent(pict)
        print(ET.tostring(pict, encoding="unicode")[:4000])
