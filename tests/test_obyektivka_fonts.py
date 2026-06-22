"""Font sizes must match reference document hierarchy."""
from __future__ import annotations

import unittest
import zipfile
from pathlib import Path

from features.obyektivka.docx_fonts import (
    ALLOWED_FONT_PTS,
    GARBAGE_EXACT,
    collect_font_sizes,
    disallowed_sizes,
    effective_sz_pt,
)
from features.obyektivka.docx_template import generate_obyektivka_docx
from features.obyektivka.docx_typography import find_runs_containing
from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "templates" / "obyektivka_master.docx"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _load_root(path: Path) -> etree._Element:
    return etree.fromstring(zipfile.ZipFile(path).read("word/document.xml"))


def _run_text(r: etree._Element) -> str:
    return "".join(t.text or "" for t in r.findall(f".//{W}t"))


class TestObyektivkaFonts(unittest.TestCase):
    def test_master_has_no_garbage_markers(self):
        if not MASTER.is_file():
            self.skipTest("master missing")
        root = _load_root(MASTER)
        for r in root.findall(f".//{W}r"):
            text = _run_text(r).strip()
            self.assertNotIn(text, GARBAGE_EXACT, f"garbage run: {text!r}")

    def test_generated_reference_font_hierarchy(self):
        if not MASTER.is_file():
            self.skipTest("master missing")
        out = ROOT / "temp" / "test_fonts.docx"
        name = "Эшматов Ботир Баҳодирович"
        path = generate_obyektivka_docx(
            {
                "fullname": name,
                "lang": "uz_cyr",
                "birthdate": "25.10.1960",
                "birthplace": "Toshkent viloyati",
                "nation": "O'zbek",
                "education": "Oliy",
                "scientific_title": "Professor",
                "work_experience": [{"year": "1977-1982", "position": "Talaba"}],
                "relatives": [],
            },
            output_filepath=str(out),
        )
        root = _load_root(Path(path))
        sizes = collect_font_sizes(root)
        bad = disallowed_sizes(sizes)
        self.assertEqual(bad, [], f"unexpected font sizes: {bad} in {sizes}")

        fish_runs = find_runs_containing(root, name)
        self.assertTrue(fish_runs)
        self.assertEqual(effective_sz_pt(fish_runs[0]), 14.0)

        body_runs = find_runs_containing(root, "25.10.1960")
        self.assertTrue(body_runs)
        self.assertEqual(effective_sz_pt(body_runs[0]), 11.0)

        mehnat_runs = find_runs_containing(root, "МЕҲНАТ ФАОЛИЯТИ")
        self.assertTrue(mehnat_runs)
        self.assertEqual(effective_sz_pt(mehnat_runs[0]), 14.0)

        rel_runs = find_runs_containing(root, "қариндошлари ҳақида")
        self.assertTrue(rel_runs)
        self.assertEqual(effective_sz_pt(rel_runs[0]), 12.0)

        allowed = set(ALLOWED_FONT_PTS)
        self.assertTrue(allowed.issuperset(sizes.keys()))


if __name__ == "__main__":
    unittest.main()
