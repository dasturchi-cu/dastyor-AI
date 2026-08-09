"""Audit font sizes in reference vs master vs generated obyektivka."""
from __future__ import annotations

import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
VAL = f"{{{W}}}val"


def load_xml(path: Path) -> etree._Element:
    return etree.fromstring(zipfile.ZipFile(path).read("word/document.xml"))


def pt_from_half(h: str | None) -> float | None:
    if not h:
        return None
    try:
        return int(h) / 2
    except ValueError:
        return None


def run_info(r: etree._Element) -> dict:
    texts = [t.text or "" for t in r.findall(f".//{W}t")]
    text = "".join(texts).strip()
    rpr = r.find(f"{W}rPr")
    p = r
    while p is not None and p.tag != f"{W}p":
        p = p.getparent()
    ppr = p.find(f"{W}pPr") if p is not None else None
    ppr_rpr = ppr.find(f"{W}pPr") if False else (ppr.find(f"{W}rPr") if ppr is not None else None)

    def sz(el):
        if el is None:
            return None
        s = el.find(f"{W}sz")
        return pt_from_half(s.get(VAL) if s is not None else None)

    r_sz = sz(rpr)
    p_sz = sz(ppr_rpr)
    bold = rpr is not None and rpr.find(f"{W}b") is not None and rpr.find(f"{W}b").get(VAL) != "0"
    underline = rpr is not None and rpr.find(f"{W}u") is not None
    style = None
    if ppr is not None:
        ps = ppr.find(f"{W}pStyle")
        if ps is not None:
            style = ps.get(f"{W}val")
    return {
        "text": text[:70],
        "r_pt": r_sz,
        "p_pt": p_sz,
        "eff_pt": r_sz or p_sz,
        "bold": bold,
        "underline": underline,
        "style": style,
    }


def audit(path: Path, label: str) -> None:
    root = load_xml(path)
    sizes = Counter()
    lines = [f"\n===== {label}: {path.name} ====="]
    for i, r in enumerate(root.findall(f".//{W}r")):
        info = run_info(r)
        if not info["text"]:
            continue
        eff = info["eff_pt"]
        if eff:
            sizes[eff] += 1
        flags = []
        if info["bold"]:
            flags.append("B")
        if info["underline"]:
            flags.append("U")
        lines.append(
            f"{eff or '?':>4}pt {' '.join(flags):2} | {info['text']}"
        )
    lines.append("SIZE COUNTS: " + ", ".join(f"{k}pt={v}" for k, v in sorted(sizes.items())))
    out = ROOT / "temp" / f"font_audit_{label}.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("written", out, "sizes", dict(sizes))


def main() -> None:
    from features.obyektivka.docx_template import generate_obyektivka_docx

    ref = ROOT / "temp" / "ref_converted.docx"
    master = ROOT / "templates" / "obyektivka_master.docx"
    gen_path = ROOT / "temp" / "font_audit_gen.docx"
    generate_obyektivka_docx(
        {
            "fullname": "Test User",
            "lang": "uz_cyr",
            "birthdate": "25.10.1960",
            "birthplace": "Toshkent",
            "nation": "O'zbek",
            "education": "Oliy",
            "work_experience": [{"year": "1977-1982", "position": "Talaba"}],
            "relatives": [],
        },
        output_filepath=str(gen_path),
    )
    audit(ref, "ref")
    audit(master, "master")
    audit(gen_path, "generated")


if __name__ == "__main__":
    main()
