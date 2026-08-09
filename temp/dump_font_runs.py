"""Dump runs with sz around page 2 title and table."""
from __future__ import annotations

import zipfile
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def dump(path: Path) -> None:
    root = etree.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
    lines = []
    for r in root.findall(f".//{W}r"):
        text = "".join(t.text or "" for t in r.findall(f".//{W}t")).strip()
        if not text:
            continue
        rpr = r.find(f"{W}rPr")
        sz = rpr.find(f"{W}sz") if rpr is not None else None
        pt = int(sz.get(f"{W}val")) / 2 if sz is not None else None
        b = rpr is not None and rpr.find(f"{W}b") is not None
        if any(k in text for k in ("МАЪЛУМОТ", "Шрифт", "пт", "МЕҲНАТ", "Қариндош", "fish", "{{fish}}")) or (pt and pt not in (11, 14)):
            lines.append(f"{pt}pt {'B' if b else '-'} | {text[:80]}")
    (ROOT / "temp" / f"runs_{path.stem}.txt").write_text("\n".join(lines), encoding="utf-8")


dump(ROOT / "temp" / "ref_converted.docx")
dump(ROOT / "templates" / "obyektivka_master.docx")
