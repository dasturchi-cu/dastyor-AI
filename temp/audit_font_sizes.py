"""Font size audit — ref vs master vs generated."""
from __future__ import annotations

import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from lxml import etree

from features.obyektivka.docx_template import generate_obyektivka_docx

ROOT = Path(__file__).resolve().parent.parent
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _effective_sz(r: etree._Element) -> float | None:
    rpr = r.find(f"{W}rPr")
    sz_el = rpr.find(f"{W}sz") if rpr is not None else None
    if sz_el is None:
        p = r
        while p is not None and p.tag != f"{W}p":
            p = p.getparent()
        if p is not None:
            ppr = p.find(f"{W}pPr")
            if ppr is not None:
                pr = ppr.find(f"{W}rPr")
                if pr is not None:
                    sz_el = pr.find(f"{W}sz")
    if sz_el is None:
        return None
    try:
        return int(sz_el.get(f"{W}val")) / 2
    except (TypeError, ValueError):
        return None


def _is_bold(r: etree._Element) -> bool:
    rpr = r.find(f"{W}rPr")
    if rpr is None:
        return False
    b = rpr.find(f"{W}b")
    return b is not None and b.get(f"{W}val") != "0"


def audit(path: Path) -> str:
    root = etree.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
    sz_counter: Counter[float] = Counter()
    bold_sz: Counter[float] = Counter()
    samples: dict[float, list[str]] = defaultdict(list)
    bad_sizes: list[str] = []

    allowed = {9.0, 10.0, 11.0, 12.0, 14.0}
    for r in root.findall(f".//{W}r"):
        text = "".join(t.text or "" for t in r.findall(f".//{W}t")).strip()
        if not text or text.startswith("Шрифт"):
            continue
        pt = _effective_sz(r)
        if pt is None:
            continue
        sz_counter[pt] += 1
        if _is_bold(r):
            bold_sz[pt] += 1
        if pt not in allowed and len(samples[pt]) < 2:
            bad_sizes.append(f"{pt}pt: {text[:60]}")
        if len(samples[pt]) < 3:
            samples[pt].append(text[:55])

    lines = [f"FILE: {path}", "SIZE COUNTS:"]
    for pt in sorted(sz_counter):
        lines.append(f"  {pt}pt -> {sz_counter[pt]} runs (bold {bold_sz[pt]}) samples={samples[pt]}")
    if bad_sizes:
        lines.append("UNEXPECTED SIZES:")
        lines.extend(f"  {x}" for x in bad_sizes)
    return "\n".join(lines)


def main() -> None:
    gen = ROOT / "temp" / "font_audit_gen.docx"
    generate_obyektivka_docx(
        {
            "fullname": "Test User",
            "lang": "uz_cyr",
            "birthdate": "25.10.1960",
            "birthplace": "Toshkent",
            "nation": "O'zbek",
            "education": "Oliy",
            "work_experience": [{"year": "1977-1982", "position": "Talaba"}],
            "relatives": [{"degree": "Otasi", "fullname": "Ali", "birth_year_place": "1950", "work_place": "X", "address": "Y"}],
        },
        output_filepath=str(gen),
    )
    out = "\n\n".join(
        [
            audit(ROOT / "temp" / "ref_converted.docx"),
            audit(ROOT / "templates" / "obyektivka_master.docx"),
            audit(gen),
        ]
    )
    (ROOT / "temp" / "font_size_audit.txt").write_text(out, encoding="utf-8")
    print("written temp/font_size_audit.txt")


if __name__ == "__main__":
    main()
