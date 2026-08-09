"""Section-specific font audit."""
from __future__ import annotations

import zipfile
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def sz_pt(r: etree._Element) -> float | None:
    rpr = r.find(f"{W}rPr")
    sz = rpr.find(f"{W}sz") if rpr is not None else None
    if sz is None:
        return None
    try:
        return int(sz.get(f"{W}val")) / 2
    except (TypeError, ValueError):
        return None


def _in_table(el: etree._Element) -> bool:
    p = el
    while p is not None:
        if p.tag == f"{W}tbl":
            return True
        p = p.getparent()
    return False


def audit_sections(path: Path) -> str:
    root = etree.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
    lines = [f"=== {path.name} ==="]

    for i, p in enumerate(root.findall(f".//{W}p")):
        if _in_table(p):
            continue
        text = "".join(t.text or "" for t in p.findall(f".//{W}t")).strip()
        if not text:
            continue
        pts = sorted({sz_pt(r) for r in p.findall(f".//{W}r") if sz_pt(r) is not None})
        ppr = p.find(f"{W}pPr")
        ps = ppr.find(f"{W}pStyle").get(f"{W}val") if ppr is not None and ppr.find(f"{W}pStyle") is not None else ""
        if any(k in text for k in ("МАЪЛУМОТ", "МЕҲНАТ", "Туғилган", "Эшматов", "{{fish}}", "Test User", "Отаси")) or pts != [11.0]:
            lines.append(f"P{i:03d} {pts}pt style={ps} | {text[:75]}")

    lines.append("\nTABLE ROWS:")
    for ti, tbl in enumerate(root.findall(f".//{W}tbl")):
        for ri, tr in enumerate(tbl.findall(f"{W}tr")):
            row_text = []
            row_pts = []
            for tc in tr.findall(f"{W}tc"):
                cell = "".join(t.text or "" for t in tc.findall(f".//{W}t")).strip()
                pts = sorted({sz_pt(r) for r in tc.findall(f".//{W}r") if sz_pt(r) is not None})
                row_pts.extend(pts)
                row_text.append(cell[:25])
            if row_pts:
                lines.append(f"T{ti}R{ri} {sorted(set(row_pts))}pt | {' | '.join(row_text)}")

    return "\n".join(lines)


for name in ["temp/ref_converted.docx", "templates/obyektivka_master.docx", "temp/font_audit_gen.docx"]:
    out = audit_sections(ROOT / name)
    (ROOT / "temp" / f"section_{Path(name).stem}.txt").write_text(out, encoding="utf-8")
    print("ok", name)
