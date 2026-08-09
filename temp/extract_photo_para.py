import re
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")

doc = zipfile.ZipFile("temp/ref_converted.docx").read("word/document.xml").decode("utf-8")
parts = re.split(r"(?=<w:p[ >])", doc)
for i, p in enumerate(parts):
    if "_x0000_s1030" in p:
        print("PARA INDEX", i)
        print(p[:8000])
        break
