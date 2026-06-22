"""Compare reference vs master vs generated DOCX structure."""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read_xml(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode("utf-8")


def plain_text(xml: str) -> str:
    return re.sub(r"<[^>]+>", "", xml)


def analyze(path: Path) -> dict:
    xml = read_xml(path)
    rel_idx = xml.find("яқин қариндошлари")
    tbl_idx = xml.find("<w:tbl>")
    mehnat_idx = xml.find("МЕҲНАТ ФАОЛИЯТИ")
    page_breaks = [
        m.start()
        for m in re.finditer(r'<w:br[^>]*w:type="page"', xml)
    ]
    sect_breaks = [m.start() for m in re.finditer(r"<w:sectPr", xml)]
    vml = "v:shape" in xml or "v:rect" in xml
  # page break between mehnat and relatives
    between = ""
    if mehnat_idx > 0 and rel_idx > mehnat_idx:
        chunk = xml[mehnat_idx:rel_idx]
        between = "page_break" if 'w:type="page"' in chunk else "no_page_break"
    return {
        "path": str(path),
        "size": len(xml),
        "tables": xml.count("<w:tbl>"),
        "page_breaks": len(page_breaks),
        "sect": len(sect_breaks),
        "vml": vml,
        "mehnat_idx": mehnat_idx,
        "rel_idx": rel_idx,
        "tbl_idx": tbl_idx,
        "rel_after_tbl": rel_idx > tbl_idx if rel_idx > 0 and tbl_idx > 0 else None,
        "mehnat_to_rel": between,
        "gridSpan": xml.count("gridSpan"),
        "paragraphs": xml.count("<w:p "),
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    paths = [
        ROOT / "temp" / "ref_converted.docx",
        ROOT / "templates" / "obyektivka_master.docx",
        ROOT / "temp" / "gen_test.docx",
    ]
    # generate test if missing
    gen = paths[2]
    if not gen.is_file():
        try:
            from features.obyektivka.docx_template import generate_obyektivka_docx

            generate_obyektivka_docx(
                {
                    "fullname": "tsrdsa",
                    "lang": "uz_cyr",
                    "birthdate": "yo'q",
                    "birthplace": "yo'q",
                    "nation": "yo'q",
                    "party": "yo'q",
                    "education": "yo'q",
                    "graduated": "yo'q",
                    "specialty": "yo'q",
                    "degree": "yo'q",
                    "scientific_title": "yo'q",
                    "languages": "yo'q",
                    "military_rank": "yo'q",
                    "awards": "yo'q",
                    "deputy": "yo'q",
                    "work_experience": [],
                    "relatives": [],
                },
                output_filepath=str(gen),
            )
        except Exception as exc:
            print("gen failed", exc)

    for p in paths:
        if p.is_file():
            info = analyze(p)
            print(info)

    # diff xml sizes
    ref = paths[0]
    master = paths[1]
    if ref.is_file() and master.is_file():
        rx, mx = read_xml(ref), read_xml(master)
        print("\nref vs master xml diff bytes:", len(mx) - len(rx))
        print("ref gridSpan", rx.count("gridSpan"), "master", mx.count("gridSpan"))
        print("ref page breaks", rx.count('w:type="page"'), "master", mx.count('w:type="page"'))


if __name__ == "__main__":
    main()
