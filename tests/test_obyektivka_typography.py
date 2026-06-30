"""Obyektivka DOCX typography — PPT: label bold, form values underlined."""
from __future__ import annotations

import unittest
import zipfile
from pathlib import Path

from features.obyektivka.docx_template import generate_obyektivka_docx
from features.obyektivka.docx_typography import (
    W,
    _is_bold_run,
    find_runs_containing,
    run_has_underline,
    typography_summary,
)
from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "templates" / "obyektivka_master.docx"


def _load_doc_xml(path: Path) -> etree._Element:
    xml = zipfile.ZipFile(path).read("word/document.xml")
    return etree.fromstring(xml)


class TestObyektivkaTypography(unittest.TestCase):
    def test_values_underlined_labels_bold(self):
        if not MASTER.is_file():
            self.skipTest("master docx missing")

        out = ROOT / "temp" / "test_typography.docx"
        path = generate_obyektivka_docx(
            {
                "fullname": "Test User",
                "lang": "uz_cyr",
                "birthdate": "25.10.1960",
                "birthplace": "Toshkent viloyati",
                "nation": "O'zbek",
                "education": "Oliy",
                "scientific_title": "Professor",
                "work_experience": [{"year": "1977-1982", "position": "Talaba"}],
                "relatives": [
                    {
                        "degree": "Otasi",
                        "fullname": "Aliyev Vali",
                        "birth_year_place": "1950",
                        "work_place": "Nafaqada",
                        "address": "Toshkent",
                    }
                ],
            },
            output_filepath=str(out),
        )
        root = _load_doc_xml(Path(path))

        date_runs = find_runs_containing(root, "25.10.1960")
        self.assertTrue(date_runs, "birthdate value missing")
        self.assertFalse(run_has_underline(date_runs[0]), "namuna: qiymatlar chiziqsiz")

        nation_runs = find_runs_containing(root, "O'zbek")
        self.assertTrue(nation_runs)
        self.assertFalse(run_has_underline(nation_runs[0]), "namuna: qiymatlar chiziqsiz")

        rel_runs = find_runs_containing(root, "Aliyev Vali")
        self.assertTrue(rel_runs)
        self.assertFalse(run_has_underline(rel_runs[0]))
        self.assertFalse(_is_bold_run(rel_runs[0]), "relatives table values must be normal weight")

        name_runs = find_runs_containing(root, "Test User")
        self.assertTrue(name_runs)
        self.assertFalse(run_has_underline(name_runs[0]))

        label_runs = find_runs_containing(root, "Миллати:")
        self.assertTrue(label_runs)
        rpr = label_runs[0].find(f"{W}rPr")
        self.assertIsNotNone(rpr)
        self.assertIsNotNone(rpr.find(f"{W}b"))
        self.assertFalse(run_has_underline(label_runs[0]))

        summary = typography_summary(root)
        self.assertGreater(summary["label_runs"], 10)

    def test_yoq_values_not_underlined(self):
        if not MASTER.is_file():
            self.skipTest("master docx missing")
        out = ROOT / "temp" / "test_yoq_no_ul.docx"
        path = generate_obyektivka_docx(
            {
                "fullname": "Test User",
                "lang": "uz_lat",
                "party": "yo'q",
                "deputy": "yo'q",
                "work_experience": [],
                "relatives": [],
            },
            output_filepath=str(out),
        )
        root = _load_doc_xml(Path(path))
        for word in ("yo'q",):
            runs = find_runs_containing(root, word)
            self.assertTrue(runs, f"missing {word!r}")
            for r in runs:
                self.assertFalse(
                    run_has_underline(r),
                    f"{word!r} must not be underlined (malumot grid)",
                )

    def test_current_job_block_separate_lines(self):
        if not MASTER.is_file():
            self.skipTest("master docx missing")

        out = ROOT / "temp" / "test_current_job.docx"
        job = "Andijon viloyati rahbari"
        year = "2007 yil 5 oktabrdan"
        path = generate_obyektivka_docx(
            {
                "fullname": "Test User",
                "lang": "uz_lat",
                "current_job": job,
                "current_job_year": year,
                "work_experience": [],
                "relatives": [],
            },
            output_filepath=str(out),
        )
        root = _load_doc_xml(Path(path))

        year_runs = find_runs_containing(root, "2007 yil 5 oktabrdan")
        job_runs = find_runs_containing(root, job)
        self.assertTrue(year_runs)
        self.assertTrue(job_runs)
        self.assertTrue(_is_bold_run(year_runs[0]))
        self.assertFalse(run_has_underline(job_runs[0]), "namuna: hozirgi ish chiziqsiz")


if __name__ == "__main__":
    unittest.main()
