"""Inspect runs: bold vs placeholder."""
from __future__ import annotations

import zipfile
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

xml = zipfile.ZipFile(ROOT / "templates" / "obyektivka_master.docx").read("word/document.xml")
root = etree.fromstring(xml)
lines = []
for r in root.findall(f".//{W}r"):
    texts = [t.text or "" for t in r.findall(f".//{W}t")]
    text = "".join(texts).strip()
    if not text:
        continue
    rpr = r.find(f"{W}rPr")
    bold = rpr is not None and rpr.find(f"{W}b") is not None
    underline = rpr is not None and rpr.find(f"{W}u") is not None
    lines.append(f"{'B' if bold else '-'}{'U' if underline else '-'} | {text[:80]}")

(ROOT / "temp" / "runs_inspect.txt").write_text("\n".join(lines[:120]), encoding="utf-8")
print("lines", len(lines))
