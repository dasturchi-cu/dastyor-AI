"""Master template must clone reference page breaks (ZIP/XML pipeline)."""
from __future__ import annotations

import unittest
from pathlib import Path

from features.obyektivka.docx_template import generate_obyektivka_docx
from features.obyektivka.docx_zip import count_page_breaks

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "temp" / "ref_converted.docx"
MASTER = ROOT / "templates" / "obyektivka_master.docx"


class TestObyektivkaLayoutClone(unittest.TestCase):
    def test_master_preserves_page_break(self):
        if not REF.is_file() or not MASTER.is_file():
            self.skipTest("reference/master docx missing")
        self.assertEqual(count_page_breaks(REF), 1)
        self.assertEqual(count_page_breaks(MASTER), count_page_breaks(REF))

    def test_generated_preserves_page_break_with_relatives(self):
        if not MASTER.is_file():
            self.skipTest("master docx missing")
        path = generate_obyektivka_docx(
            {
                "fullname": "Test User",
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
            output_filepath=str(ROOT / "temp" / "test_layout_clone.docx"),
        )
        self.assertEqual(count_page_breaks(Path(path)), count_page_breaks(MASTER))

    def test_generated_omits_page_break_without_relatives(self):
        if not MASTER.is_file():
            self.skipTest("master docx missing")
        path = generate_obyektivka_docx(
            {
                "fullname": "Test User",
                "lang": "uz_cyr",
                "work_experience": [],
                "relatives": [],
            },
            output_filepath=str(ROOT / "temp" / "test_layout_clone_empty.docx"),
        )
        self.assertEqual(count_page_breaks(Path(path)), 0)


if __name__ == "__main__":
    unittest.main()
