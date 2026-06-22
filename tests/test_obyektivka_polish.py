"""Tests for PPT/reference polish pass."""
from __future__ import annotations

import unittest
import zipfile
from pathlib import Path

from features.obyektivka.docx_template import generate_obyektivka_docx
from features.obyektivka.docx_typography import VAL, W, _is_bold_run, find_runs_containing
from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "templates" / "obyektivka_master.docx"


def _load_root(path: Path) -> etree._Element:
    return etree.fromstring(zipfile.ZipFile(path).read("word/document.xml"))


def _paragraph_jc(p_el: etree._Element) -> str:
    ppr = p_el.find(f"{W}pPr")
    if ppr is None:
        return ""
    jc = ppr.find(f"{W}jc")
    return jc.get(VAL) if jc is not None else ""


def _run_color(r_el: etree._Element) -> str:
    rpr = r_el.find(f"{W}rPr")
    if rpr is None:
        return ""
    c = rpr.find(f"{W}color")
    return c.get(VAL) if c is not None else ""


class TestObyektivkaPolish(unittest.TestCase):
    def test_malumotnoma_centered_bold_black(self):
        if not MASTER.is_file():
            self.skipTest("master missing")
        out = ROOT / "temp" / "test_polish.docx"
        path = generate_obyektivka_docx(
            {
                "fullname": "Test User",
                "lang": "uz_cyr",
                "birthdate": "25.10.1960",
                "nation": "O'zbek",
                "work_experience": [],
                "relatives": [],
            },
            output_filepath=str(out),
        )
        root = _load_root(Path(path))
        title_p = None
        for p in root.findall(f".//{W}p"):
            txt = "".join(t.text or "" for t in p.findall(f".//{W}t"))
            if "МАЪЛУМОТНОМА" in txt:
                title_p = p
                break
        self.assertIsNotNone(title_p)
        self.assertEqual(_paragraph_jc(title_p), "center")
        runs = find_runs_containing(root, "МАЪЛУМОТНОМА")
        self.assertTrue(runs)
        self.assertTrue(_is_bold_run(runs[0]))
        self.assertEqual(_run_color(runs[0]), "000000")

    def test_value_not_bold_label_bold(self):
        if not MASTER.is_file():
            self.skipTest("master missing")
        out = ROOT / "temp" / "test_polish_vals.docx"
        path = generate_obyektivka_docx(
            {
                "fullname": "Test User",
                "lang": "uz_cyr",
                "birthdate": "25.10.1960",
                "nation": "O'zbek",
                "work_experience": [],
                "relatives": [],
            },
            output_filepath=str(out),
        )
        root = _load_root(Path(path))
        nation = find_runs_containing(root, "O'zbek")
        millat = find_runs_containing(root, "Миллати:")
        self.assertTrue(nation)
        self.assertTrue(millat)
        self.assertFalse(_is_bold_run(nation[0]))
        self.assertTrue(_is_bold_run(millat[0]))


if __name__ == "__main__":
    unittest.main()
