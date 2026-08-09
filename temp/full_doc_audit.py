"""To'liq hujjat audit: preview / demo / paid + namuna."""
from __future__ import annotations

import io
import sys
import zipfile
from collections import Counter
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from features.obyektivka.docx_template import generate_obyektivka_docx_bytes

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
VAL = W + "val"


def load_body(path_or_bytes: Path | bytes) -> etree._Element:
    if isinstance(path_or_bytes, bytes):
        xml = zipfile.ZipFile(io.BytesIO(path_or_bytes)).read("word/document.xml")
    else:
        xml = zipfile.ZipFile(path_or_bytes).read("word/document.xml")
    return etree.fromstring(xml)


def margins(root: etree._Element) -> dict[str, int]:
    pg = root.find(f".//{W}sectPr/{W}pgMar")
    if pg is None:
        return {}
    return {k: int(pg.get(f"{W}{k}") or 0) for k in ("top", "right", "bottom", "left")}


def font_pt_counts(root: etree._Element) -> dict[float, int]:
    c: Counter[float] = Counter()
    for r in root.findall(f".//{W}r"):
        t = "".join(x.text or "" for x in r.findall(f".//{W}t")).strip()
        if not t:
            continue
        rpr = r.find(f"{W}rPr")
        if rpr is None:
            continue
        sz = rpr.find(f"{W}sz")
        if sz is not None and sz.get(VAL):
            c[int(sz.get(VAL)) / 2] += 1
    return dict(c)


def colors_used(root: etree._Element) -> set[str]:
    out: set[str] = set()
    for c in root.findall(f".//{W}color"):
        v = c.get(VAL)
        if v:
            out.add(v.upper())
    return out


def underline_runs(root: etree._Element) -> int:
    n = 0
    for rpr in root.findall(f".//{W}rPr"):
        u = rpr.find(f"{W}u")
        if u is not None and u.get(VAL) != "none":
            n += 1
    return n


def page_breaks(data: bytes) -> int:
    xml = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml").decode("utf-8")
    return xml.count('w:type="page"')


def section_flags(root: etree._Element) -> dict[str, bool]:
    text = "".join(t.text or "" for t in root.findall(f".//{W}t"))
    low = text.casefold()
    return {
        "malumotnoma": "МАЪЛУМОТНОМА" in text or "MA'LUMOTNOMA" in text,
        "fish": "{{fish}}" not in text and bool(text.strip()),
        "mehnat": "МЕҲНАТ ФАОЛИЯТИ" in text or "MEHNAT FAOLIYATI" in text,
        "rel_intro": "қариндошлари ҳақида" in text or "qarindoshlari haqida" in low,
        "rel_malumot": "МАЪЛУМОТ" in text,
        "rel_table": any(
            "qarindosh" in "".join(t.text or "" for t in tbl.findall(f".//{W}t")).casefold()
            or "қариндош" in "".join(t.text or "" for t in tbl.findall(f".//{W}t"))
            for tbl in root.findall(f".//{W}tbl")
        ),
        "yoq_in_body": "yo'q" in low or "йўқ" in text,
    }


def body_paragraph_spacing(root: etree._Element) -> list[tuple[str, dict]]:
    body = root.find(f"{W}body")
    out: list[tuple[str, dict]] = []
    if body is None:
        return out
    for p in body.findall(f"{W}p"):
        txt = "".join(t.text or "" for t in p.findall(f".//{W}t")).strip()[:42]
        if not txt:
            continue
        ppr = p.find(f"{W}pPr")
        sp: dict[str, str] = {}
        ind: dict[str, str] = {}
        jc = ""
        if ppr is not None:
            s = ppr.find(f"{W}spacing")
            if s is not None:
                sp = {k: s.get(f"{W}{k}") for k in ("before", "after", "line", "lineRule") if s.get(f"{W}{k}")}
            ii = ppr.find(f"{W}ind")
            if ii is not None:
                ind = {
                    k: ii.get(f"{W}{k}")
                    for k in ("left", "right", "hanging", "firstLine")
                    if ii.get(f"{W}{k}")
                }
            j = ppr.find(f"{W}jc")
            if j is not None:
                jc = j.get(VAL) or ""
        out.append((txt, {"sp": sp, "ind": ind, "jc": jc}))
    return out


def compare_spacing(a: list, b: list, label: str) -> list[str]:
    diffs: list[str] = []
    n = min(len(a), len(b))
    for i in range(n):
        if a[i][1] != b[i][1]:
            diffs.append(f"  p{i} {a[i][0]!r}: gen={a[i][1]} master={b[i][1]}")
    if len(a) != len(b):
        diffs.append(f"  paragraf soni: gen={len(a)} master={len(b)}")
    return [f"[{label}]"] + diffs[:12] if diffs else []


def zip_parts(data: bytes) -> set[str]:
    return set(zipfile.ZipFile(io.BytesIO(data)).namelist())


def main() -> None:
    full = {
        "fullname": "Эшматов Ботир Баҳодирович",
        "lang": "uz_cyr",
        "birthdate": "25.10.1960",
        "birthplace": "Тошкент вилояти, Қибрай тумани",
        "nation": "ўзбек",
        "party": "йўқ",
        "education": "олий",
        "graduated": "1982 й. Тошкент давлат университети",
        "specialty": "иқтисодчи",
        "degree": "иқтисод фанлари доктори",
        "scientific_title": "профессор",
        "languages": "рус, инглиз тиллари",
        "military_rank": "йўқ",
        "awards": "2005 й. медал",
        "departmental_awards": "2008 й. нишон",
        "deputy": "2024 й. депутат",
        "current_job_year": "2007 йил 5 октябрдан:",
        "current_job": "Андижон вилояти раҳбари",
        "work_experience": [
            {"year": "1977-1982", "position": "Талаба"},
            {"year": "1982-1988", "position": "Илмий ходим"},
        ],
        "relatives": [
            {
                "degree": "Отаси",
                "fullname": "Aliyev Vali",
                "birth_year_place": "1950",
                "work_place": "Nafaqada",
                "address": "Toshkent",
            }
        ],
    }
    minimal = {"fullname": "Test", "lang": "uz_cyr", "relatives": []}

    master = ROOT / "templates" / "obyektivka_master.docx"
    ref = ROOT / "temp" / "ref_converted.docx"

    preview = generate_obyektivka_docx_bytes(full, watermark=False)
    demo = generate_obyektivka_docx_bytes(full, watermark=True)
    paid = generate_obyektivka_docx_bytes(full, watermark=False)
    minimal_doc = generate_obyektivka_docx_bytes(minimal, watermark=False)

    r_preview = load_body(preview)
    r_paid = load_body(paid)
    r_demo = load_body(demo)
    r_min = load_body(minimal_doc)
    r_master = load_body(master) if master.is_file() else None

    print("=" * 60)
    print("1. PREVIEW vs PAID (Word yuklab olish)")
    print("=" * 60)
    print("  document.xml bir xil:", zipfile.ZipFile(io.BytesIO(preview)).read("word/document.xml")
          == zipfile.ZipFile(io.BytesIO(paid)).read("word/document.xml"))
    print("  ZIP fayl bir xil:", preview == paid)

    print("\n" + "=" * 60)
    print("2. PREVIEW vs DEMO (faqat watermark farqi)")
    print("=" * 60)
    print("  document.xml bir xil:", zipfile.ZipFile(io.BytesIO(preview)).read("word/document.xml")
          == zipfile.ZipFile(io.BytesIO(demo)).read("word/document.xml"))
    demo_only = zip_parts(demo) - zip_parts(preview)
    print("  Demo qo'shimcha fayllar:", sorted(demo_only) or "yo'q")

    print("\n" + "=" * 60)
    print("3. BO'LIMLAR (to'liq ma'lumot + 1 qarindosh)")
    print("=" * 60)
    for name, root in [("preview", r_preview), ("demo", r_demo), ("paid", r_paid)]:
        f = section_flags(root)
        print(f"  {name}: {f}")

    print("\n" + "=" * 60)
    print("4. MARGIN / SAHIFA / SHRIFT / RANG")
    print("=" * 60)
    for name, root, data in [
        ("preview", r_preview, preview),
        ("demo", r_demo, demo),
        ("paid", r_paid, paid),
        ("minimal", r_min, minimal_doc),
    ]:
        print(f"  [{name}] margins={margins(root)} page_breaks={page_breaks(data)}")
        print(f"         fonts_pt={font_pt_counts(root)} colors={sorted(colors_used(root))} underline={underline_runs(root)}")

    if r_master is not None:
        print("\n" + "=" * 60)
        print("5. YARATILGAN vs MASTER SHABLON (spacing/indent)")
        print("=" * 60)
        gen_sp = body_paragraph_spacing(r_preview)
        mas_sp = body_paragraph_spacing(r_master)
        diffs = compare_spacing(gen_sp, mas_sp, "gen vs master")
        if diffs:
            print("\n".join(diffs))
            print(f"  ... jami farqli qatorlar: {sum(1 for d in diffs if d.startswith('  p'))}")
        else:
            print("  Birinchi qatorlar bo'yicha spacing/indent farqi yo'q")

        print(f"  margins master={margins(r_master)} gen={margins(r_preview)}")
        print(f"  margins mos:", margins(r_master) == margins(r_preview))

    if ref.is_file():
        r_ref = load_body(ref)
        print("\n" + "=" * 60)
        print("6. NAMUNA (ref) vs YARATILGAN")
        print("=" * 60)
        print(f"  margins ref={margins(r_ref)} gen={margins(r_preview)}")
        print(f"  page_breaks ref={page_breaks(ref.read_bytes())} gen={page_breaks(preview)}")
        print(f"  underline runs ref={underline_runs(r_ref)} gen={underline_runs(r_preview)}")

    print("\n" + "=" * 60)
    print("7. BO'SH QARINDOSHLAR (1-sahifa faqat)")
    print("=" * 60)
    f = section_flags(r_min)
    print(f"  rel_table={f['rel_table']} rel_intro={f['rel_intro']} page_breaks={page_breaks(minimal_doc)}")
    print(f"  mehnat={f['mehnat']} malumotnoma={f['malumotnoma']}")

    print("\n" + "=" * 60)
    print("8. XULOSA")
    print("=" * 60)
    checks = [
        ("Preview = Paid matn", preview == paid),
        ("Demo matn = Preview matn", zipfile.ZipFile(io.BytesIO(preview)).read("word/document.xml")
         == zipfile.ZipFile(io.BytesIO(demo)).read("word/document.xml")),
        ("Marginlar mos", margins(r_preview) == margins(r_master) if r_master is not None else True),
        ("Qarindosh bor → jadval", section_flags(r_preview)["rel_table"]),
        ("Qarindosh yo'q → jadval yo'q", not section_flags(r_min)["rel_table"]),
        ("Barcha matn qora", colors_used(r_preview) <= {"000000"} or colors_used(r_preview) == {"000000"}),
        ("Mehnat bo'limi bor", section_flags(r_preview)["mehnat"]),
        ("Malumotnoma bor", section_flags(r_preview)["malumotnoma"]),
    ]
    for label, ok in checks:
        print(f"  {'✓' if ok else '✗'} {label}")


if __name__ == "__main__":
    main()
