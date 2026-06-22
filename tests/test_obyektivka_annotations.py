"""Reference-lock mode: developer annotations must never appear in output."""
from __future__ import annotations

import re
import unittest
import zipfile
from pathlib import Path

from features.obyektivka.docx_annotations import collect_annotation_violations
from features.obyektivka.docx_template import generate_obyektivka_docx

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "templates" / "obyektivka_master.docx"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _load_root(path: Path):
    from lxml import etree

    return etree.fromstring(zipfile.ZipFile(path).read("word/document.xml"))


def _xml_text(path: Path) -> str:
    return zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")


class TestObyektivkaAnnotations(unittest.TestCase):
    def test_master_has_no_developer_annotations(self):
        if not MASTER.is_file():
            self.skipTest("master missing")
        root = _load_root(MASTER)
        violations = collect_annotation_violations(root)
        self.assertEqual(violations, [], f"master annotations: {violations}")

    def test_generated_has_no_developer_annotations(self):
        if not MASTER.is_file():
            self.skipTest("master missing")
        out = ROOT / "temp" / "test_annotations.docx"
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
        violations = collect_annotation_violations(root)
        self.assertEqual(violations, [], f"generated annotations: {violations}")

        xml = _xml_text(Path(path))
        self.assertNotRegex(xml, r"Шрифт\s+\d+", "Шрифт label leaked")
        self.assertNotRegex(xml, r"Shrift\s+\d+", "Shrift label leaked")
        self.assertNotIn("фақат", xml, "military training bubble leaked")
        self.assertNotIn("кўрсатилади", xml, "military training bubble leaked")
        self.assertEqual(xml.count("<w:pict"), 1, "only photo VML frame should remain")

    def test_master_has_tamomlagan_placeholder(self):
        if not MASTER.is_file():
            self.skipTest("master missing")
        xml = _xml_text(MASTER)
        self.assertIn("{{tamomlagan}}", xml)
        self.assertNotIn("1982 й. Тошкент давлат университети", xml)


if __name__ == "__main__":
    unittest.main()
