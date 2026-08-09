"""Compare namuna ref vs master vs generated DOCX."""
from __future__ import annotations

import sys
import zipfile
from collections import Counter
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
VAL = W + "val"


def load(path: Path) -> etree._Element:
    return etree.fromstring(zipfile.ZipFile(path).read("word/document.xml"))


def margins(root: etree._Element) -> dict[str, int]:
    pg = root.find(f".//{W}sectPr/{W}pgMar")
    if pg is None:
        return {}
    return {k: int(pg.get(f"{W}{k}") or 0) for k in ("top", "right", "bottom", "left")}


def font_sizes(root: etree._Element) -> Counter[float]:
    out: Counter[float] = Counter()
    for r in root.findall(f".//{W}r"):
        rpr = r.find(f"{W}rPr")
        if rpr is None:
            continue
        sz = rpr.find(f"{W}sz")
        if sz is not None and sz.get(VAL):
            out[int(sz.get(VAL)) / 2] += 1
    return out


def para_count(root: etree._Element) -> tuple[int, int]:
    body = root.find(f"{W}body")
    if body is None:
        return 0, 0
    return len(body.findall(f"{W}p")), len(body.findall(f"{W}tbl"))


def page_breaks(path: Path) -> int:
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    return xml.count('w:type="page"')


def underline_count(root: etree._Element) -> int:
    n = 0
    for rpr in root.findall(f".//{W}rPr"):
        u = rpr.find(f"{W}u")
        if u is not None and u.get(VAL) != "none":
            n += 1
    return n


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    from features.obyektivka.docx_template import generate_obyektivka_docx

    sample = {
        "fullname": "Эшматов Ботир Баҳодирович",
        "lang": "uz_cyr",
        "birthdate": "25.10.1960",
        "birthplace": "Тошкент",
        "nation": "ўзбек",
        "party": "йўқ",
        "education": "олий",
        "work_experience": [{"year": "1977-1982", "position": "Талаба"}],
        "relatives": [
            {
                "degree": "Отаси",
                "fullname": "Test Ota",
                "birth_year_place": "1950",
                "work_place": "x",
                "address": "y",
            }
        ],
    }
    gen = ROOT / "temp" / "compare_gen.docx"
    generate_obyektivka_docx(sample, output_filepath=str(gen))

    files = {
        "namuna (ref)": ROOT / "temp" / "ref_converted.docx",
        "master shablon": ROOT / "templates" / "obyektivka_master.docx",
        "yaratilgan": gen,
    }

    print("=== MARGINLAR (twips) ===")
    for name, p in files.items():
        print(f"  {name}: {margins(load(p))}")

    print("\n=== SHRIFT O'LCHAMLARI (pt, soni) ===")
    for name, p in files.items():
        print(f"  {name}: {dict(font_sizes(load(p)))}")

    print("\n=== PARAGRAF / JADVAL / SAHIFA ===")
    for name, p in files.items():
        pc, tc = para_count(load(p))
        print(f"  {name}: p={pc} tbl={tc} page_breaks={page_breaks(p)} underline_runs={underline_count(load(p))}")

    ref = load(files["namuna (ref)"])
    mas = load(files["master shablon"])
    gen_r = load(files["yaratilgan"])

    print("\n=== NAMUNA vs MASTER ===")
    rm, mm = margins(ref), margins(mas)
    print(f"  margin farq: {{{', '.join(f'{k}: {mm[k]-rm[k]}' for k in rm)}}}")
    fd = font_sizes(mas) - font_sizes(ref)
    print(f"  shrift farq (master-namuna): {dict(fd) if fd else 'yo\'q'}")

    print("\n=== NAMUNA vs YARATILGAN ===")
    gm = margins(gen_r)
    print(f"  margin farq: {{{', '.join(f'{k}: {gm[k]-rm[k]}' for k in rm)}}}")
    fd2 = font_sizes(gen_r) - font_sizes(ref)
    print(f"  shrift farq: {dict(fd2) if fd2 else 'yo\'q'}")
    print(f"  paragraf: namuna={para_count(ref)[0]} yaratilgan={para_count(gen_r)[0]}")


if __name__ == "__main__":
    main()
