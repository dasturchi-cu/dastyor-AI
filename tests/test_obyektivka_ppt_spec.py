"""PPT namuna format talablari — margin, jadval chiziqlari."""
from __future__ import annotations

import unittest
import zipfile
from pathlib import Path

from features.obyektivka.docx_template import generate_obyektivka_docx
from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "templates" / "obyektivka_master.docx"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
VAL = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val"


def _load_root(path: Path) -> etree._Element:
    return etree.fromstring(zipfile.ZipFile(path).read("word/document.xml"))


def _margins_mm(root: etree._Element) -> dict[str, float]:
    sect = root.find(f".//{W}sectPr")
    pg = sect.find(f"{W}pgMar") if sect is not None else None
    if pg is None:
        return {}
    twips_to_mm = 25.4 / 1440
    return {
        side: round(int(pg.get(f"{W}{side}") or 0) * twips_to_mm, 1)
        for side in ("top", "right", "bottom", "left")
    }


class TestObyektivkaPptSpec(unittest.TestCase):
    def test_page_margins_ppt(self):
        if not MASTER.is_file():
            self.skipTest("master missing")
        out = ROOT / "temp" / "test_ppt_margins.docx"
        path = generate_obyektivka_docx(
            {"fullname": "Test", "lang": "uz_cyr", "work_experience": [], "relatives": []},
            output_filepath=str(out),
        )
        m = _margins_mm(_load_root(Path(path)))
        self.assertAlmostEqual(m["top"], 15.0, delta=0.5)
        self.assertAlmostEqual(m["bottom"], 5.9, delta=0.8)
        self.assertAlmostEqual(m["left"], 26.9, delta=0.5)
        self.assertAlmostEqual(m["right"], 10.0, delta=0.5)

    def test_relatives_table_centered(self):
        if not MASTER.is_file():
            self.skipTest("master missing")
        out = ROOT / "temp" / "test_ppt_center.docx"
        path = generate_obyektivka_docx(
            {"fullname": "Test", "lang": "uz_cyr", "work_experience": [], "relatives": []},
            output_filepath=str(out),
        )
        root = _load_root(Path(path))
        tbl = root.find(f".//{W}tbl")
        self.assertIsNotNone(tbl)
        tbl_pr = tbl.find(f"{W}tblPr")
        jc = tbl_pr.find(f"{W}jc") if tbl_pr is not None else None
        self.assertIsNotNone(jc)
        self.assertEqual(jc.get(VAL), "center")
        self.assertIsNone(tbl_pr.find(f"{W}tblInd"))

    def test_relatives_table_borders_1pt(self):
        if not MASTER.is_file():
            self.skipTest("master missing")
        out = ROOT / "temp" / "test_ppt_borders.docx"
        path = generate_obyektivka_docx(
            {
                "fullname": "Test",
                "lang": "uz_cyr",
                "work_experience": [],
                "relatives": [
                    {
                        "degree": "Otasi",
                        "fullname": "Aliyev",
                        "birth_year_place": "1950",
                        "work_place": "Nafaqada",
                        "address": "Toshkent",
                    }
                ],
            },
            output_filepath=str(out),
        )
        root = _load_root(Path(path))
        tbl = root.find(f".//{W}tbl")
        self.assertIsNotNone(tbl)
        borders = tbl.find(f".//{W}tblBorders")
        self.assertIsNotNone(borders)
        top = borders.find(f"{W}top")
        self.assertIsNotNone(top)
        self.assertEqual(top.get(VAL), "single")
        self.assertEqual(top.get(f"{W}sz"), "8")
        self.assertEqual(top.get(f"{W}color"), "000000")


if __name__ == "__main__":
    unittest.main()
