"""Qarindoshlar bo'limi: preview / demo / paid bir xilligi."""
from __future__ import annotations

import io
import sys
import zipfile

from lxml import etree

sys.stdout.reconfigure(encoding="utf-8")

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from features.obyektivka.docx_template import generate_obyektivka_docx_bytes

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
VAL = W + "val"


def rel_section_sig(data: bytes) -> dict:
    root = etree.fromstring(zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml"))
    body = root.find(f"{W}body")
    tbl = None
    intro = mal = False
    for el in body:
        if el.tag == f"{W}p":
            t = "".join(x.text or "" for x in el.findall(f".//{W}t")).strip()
            low = t.casefold()
            if "qarindosh" in low or "қариндош" in low:
                intro = True
            if t.strip() in ("МАЪЛУМОТ", "MA'LUMOT"):
                mal = True
        elif el.tag == f"{W}tbl":
            blob = "".join(x.text or "" for x in el.findall(f".//{W}t")).casefold()
            if "qarindosh" in blob or "қариндош" in blob or "turar joyi" in blob:
                tbl = el
    if tbl is None:
        return {"has_table": False, "intro": intro, "mal": mal}
    tbl_pr = tbl.find(f"{W}tblPr")
    jc = tw = borders = ""
    if tbl_pr is not None:
        j = tbl_pr.find(f"{W}jc")
        jc = j.get(VAL) if j is not None else ""
        tw_el = tbl_pr.find(f"{W}tblW")
        tw = tw_el.get(f"{W}w") if tw_el is not None else ""
        b = tbl_pr.find(f"{W}tblBorders")
        if b is not None:
            top = b.find(f"{W}top")
            if top is not None:
                borders = f"{top.get(VAL)}/{top.get(f'{W}sz')}/{top.get(f'{W}color')}"
    trs = tbl.findall(f"{W}tr")
    rows = []
    colors: set[str] = set()
    for tr in trs[1:]:
        cells = [
            "".join(x.text or "" for x in tc.findall(f".//{W}t")).strip()
            for tc in tr.findall(f"{W}tc")
        ]
        rows.append(cells)
        for r in tr.findall(f".//{W}r"):
            c = r.find(f".//{W}rPr/{W}color")
            if c is not None:
                colors.add(c.get(VAL) or "")
    return {
        "has_table": True,
        "intro": intro,
        "mal": mal,
        "jc": jc,
        "tw": tw,
        "border": borders,
        "rows": rows,
        "row_count": len(trs) - 1,
        "colors": sorted(colors),
    }


def body_xml(b: bytes) -> bytes:
    return zipfile.ZipFile(io.BytesIO(b)).read("word/document.xml")


def main() -> None:
    payload = {
        "fullname": "Test User",
        "lang": "uz_cyr",
        "birthdate": "25.10.1960",
        "birthplace": "Toshkent",
        "relatives": [
            {
                "degree": "Otasi",
                "fullname": "Aliyev Vali",
                "birth_year_place": "1950",
                "work_place": "Nafaqada",
                "address": "Toshkent",
            },
            {
                "degree": "Onasi",
                "fullname": "Aliyeva Malika",
                "birth_year_place": "1955",
                "work_place": "Uy bekasi",
                "address": "Toshkent",
            },
        ],
    }
    empty = {"fullname": "Test User", "lang": "uz_cyr", "relatives": []}

    results: dict[str, bytes] = {}
    for label, wm in [("preview", False), ("demo", True), ("paid", False)]:
        results[label] = generate_obyektivka_docx_bytes(payload, watermark=wm)
        print(f"=== {label} ===")
        print(rel_section_sig(results[label]))
        print()

    print("=== empty relatives ===")
    print(rel_section_sig(generate_obyektivka_docx_bytes(empty, watermark=False)))
    print()
    print("preview body == paid body:", body_xml(results["preview"]) == body_xml(results["paid"]))
    print("preview body == demo body:", body_xml(results["preview"]) == body_xml(results["demo"]))
    print("preview file == paid file:", results["preview"] == results["paid"])


if __name__ == "__main__":
    main()
