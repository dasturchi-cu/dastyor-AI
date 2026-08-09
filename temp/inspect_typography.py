"""Inspect obyektivka master DOCX typography."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
xml = zipfile.ZipFile(ROOT / "templates" / "obyektivka_master.docx").read("word/document.xml").decode("utf-8")

labels = [
    "Туғилган йили",
    "Миллати",
    "Маълумоти",
    "Илмий унвони",
    "{{tugilgan_sana}}",
    "{{millati}}",
    "{{mehnat_faoliyati}}",
    "Отаси",
]

out = []
for label in labels:
    i = xml.find(label)
    if i < 0:
        out.append(f"{label}: NOT FOUND\n")
        continue
    snip = xml[max(0, i - 350) : i + len(label) + 250]
    out.append(f"=== {label} ===\n")
    out.append(f"has w:b: {'<w:b' in snip}\n")
    out.append(f"has w:u: {'<w:u' in snip}\n")
    out.append(snip + "\n\n")

# count placeholders
phs = re.findall(r"\{\{[^}]+\}\}", xml)
out.append(f"placeholders: {len(phs)}\n")

(ROOT / "temp" / "typography_inspect.txt").write_text("".join(out), encoding="utf-8")
print("written temp/typography_inspect.txt")
