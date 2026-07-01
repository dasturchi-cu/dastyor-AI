"""Reference Document Lock Mode — full success criteria from namuna template."""
from __future__ import annotations

import re
import unittest
import zipfile
from pathlib import Path

from features.obyektivka.docx_annotations import collect_annotation_violations
from features.obyektivka.docx_fonts import ALLOWED_FONT_PTS, collect_font_sizes, disallowed_sizes
from features.obyektivka.docx_template import generate_obyektivka_docx
from features.obyektivka.docx_zip import count_page_breaks
from features.obyektivka.layout import REL_COL_DXA
from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "temp" / "ref_converted.docx"
MASTER = ROOT / "templates" / "obyektivka_master.docx"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"


def _load_root(path: Path) -> etree._Element:
    return etree.fromstring(zipfile.ZipFile(path).read("word/document.xml"))


def _xml(path: Path) -> str:
    return zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")


def _margins_twips(root: etree._Element) -> dict[str, str]:
    sect = root.find(f".//{W}sectPr")
    pg = sect.find(f"{W}pgMar") if sect is not None else None
    if pg is None:
        return {}
    return {k: pg.get(f"{W}{k}") or "" for k in ("top", "right", "bottom", "left")}


def _table_grid_dxa(root: etree._Element) -> list[str]:
    tbl = root.find(f".//{W}tbl")
    if tbl is None:
        return []
    g = tbl.find(f"{W}tblGrid")
    if g is None:
        return []
    return [c.get(f"{W}w") or "" for c in g.findall(f"{W}gridCol")]


class TestObyektivkaReferenceLock(unittest.TestCase):
    """Template clone mode: layout from reference, annotations never rendered."""

    def test_master_matches_reference_structure(self):
        if not REF.is_file() or not MASTER.is_file():
            self.skipTest("reference/master docx missing")
        ref_root = _load_root(REF)
        master_root = _load_root(MASTER)
        self.assertEqual(_margins_twips(ref_root), _margins_twips(master_root))
        self.assertEqual(_table_grid_dxa(ref_root), _table_grid_dxa(master_root))
        self.assertEqual(_table_grid_dxa(master_root), ['1260', '2160', '1830', '3027', '2057'])
        self.assertEqual(count_page_breaks(MASTER), count_page_breaks(REF))

    def test_no_developer_annotations_in_output(self):
        if not MASTER.is_file():
            self.skipTest("master missing")
        out = ROOT / "temp" / "test_reference_lock.docx"
        path = generate_obyektivka_docx(
            {
                "fullname": "Эшматов Ботир Баҳодирович",
                "lang": "uz_cyr",
                "birthdate": "25.10.1960",
                "birthplace": "Toshkent viloyati",
                "nation": "O'zbek",
                "education": "Oliy",
                "graduated": "1982 y. Universitet",
                "specialty": "iqtisodchi",
                "scientific_title": "Professor",
                "work_experience": [{"year": "1977-1982", "position": "Talaba"}],
                "relatives": [],
            },
            output_filepath=str(out),
        )
        root = _load_root(Path(path))
        xml = _xml(Path(path))

        violations = collect_annotation_violations(root)
        self.assertEqual(violations, [], f"annotation leak: {violations}")

        for pattern, label in (
            (r"Shrift\s+\d+", "Shrift label"),
            (r"Шрифт\s+\d+", "Шрифт label"),
            (r"\d+\s*mm\b", "mm measurement"),
            (r"\d+\s*мм\b", "mm measurement (cyr)"),
        ):
            self.assertNotRegex(xml, pattern, f"{label} leaked into output")

        self.assertNotIn("фақат", xml)
        self.assertNotIn("кўрсатилади", xml)
        self.assertEqual(xml.count("<w:pict"), 1, "only photo VML frame should remain")
        self.assertEqual(xml.count("v:line"), 0, "arrow shapes must be stripped")
        self.assertEqual(xml.count("v:polyline"), 0, "arrow shapes must be stripped")

    def test_typography_from_reference_hierarchy(self):
        if not MASTER.is_file():
            self.skipTest("master missing")
        out = ROOT / "temp" / "test_reference_lock_fonts.docx"
        path = generate_obyektivka_docx(
            {
                "fullname": "Test User",
                "lang": "uz_cyr",
                "birthdate": "25.10.1960",
                "work_experience": [],
                "relatives": [],
            },
            output_filepath=str(out),
        )
        root = _load_root(Path(path))
        sizes = collect_font_sizes(root)
        bad = disallowed_sizes(sizes)
        self.assertEqual(bad, [], f"non-reference font sizes: {bad}")
        self.assertTrue(set(sizes).issubset(set(ALLOWED_FONT_PTS)))

    def test_generated_preserves_clone_layout(self):
        if not MASTER.is_file():
            self.skipTest("master missing")
        out = ROOT / "temp" / "test_reference_lock_layout.docx"
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
        master_root = _load_root(MASTER)
        gen_root = _load_root(Path(path))
        self.assertEqual(_table_grid_dxa(gen_root), [str(w) for w in REL_COL_DXA])
        self.assertEqual(count_page_breaks(Path(path)), count_page_breaks(MASTER))


if __name__ == "__main__":
    unittest.main()
