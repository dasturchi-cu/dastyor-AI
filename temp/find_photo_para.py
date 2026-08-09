import re
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")

doc = zipfile.ZipFile("temp/ref_converted.docx").read("word/document.xml").decode()
# strip txbxContent to avoid false paragraph splits
clean = re.sub(r"<w:txbxContent>.*?</w:txbxContent>", "<w:txbxContent/>", doc, flags=re.S)
parts = re.split(r"(?=<w:p[ >])", clean)
for i, p in enumerate(parts[:8]):
    has_rect = "_x0000_s1030" in p or "v:rect" in p
    text = re.sub(r"<[^>]+>", "", p)
    text = re.sub(r"\s+", " ", text).strip()[:100]
    print(i, "rect=", has_rect, "text=", repr(text))
