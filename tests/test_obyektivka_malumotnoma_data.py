"""Mehnat faoliyati — bitta manba, barcha chiqishlar bir xil."""
from __future__ import annotations

import re
import unittest

from backend.services.document_render.context import build_obyektivka_render_context
from features.obyektivka.malumotnoma_data import build_malumotnoma_data
from features.obyektivka.placeholders import build_placeholder_context


def _sample_payload() -> dict:
    return {
        "lang": "uz_lat",
        "fullname": "Test User",
        "work_experience": [
            {"f": "2001", "t": "2005", "d": "Birinchi ish"},
            {"f": "2005", "t": "2007", "d": "Ikkinchi ish"},
            {"f": "2007", "t": "h.v", "d": "MCHJ rahbari"},
        ],
    }


class TestMalumotnomaEmployment(unittest.TestCase):
    def test_three_jobs_current_at_top_and_in_history(self):
        data = build_malumotnoma_data(_sample_payload())
        self.assertEqual(data["current_job"], "MCHJ rahbari")
        self.assertEqual(data["current_job_year"], "2007-yildan:")
        self.assertEqual(len(data["work_experience"]), 3)
        self.assertEqual(len(data["work_lines"]), 3)
        self.assertIn("h.v", data["work_lines"][-1])
        self.assertIn("MCHJ rahbari", data["work_lines"][-1])

    def test_preview_matches_docx_work_lines(self):
        raw = _sample_payload()
        preview = build_obyektivka_render_context(raw)
        docx = build_placeholder_context(raw)
        self.assertEqual(preview["current_job"], docx["hozirgi_ish"])
        self.assertEqual(preview["current_job_year"], docx["hozirgi_yil"])
        preview_lines = [
            f"{w['year']} - {w['position']}" if w.get("year") and w.get("position") else w.get("year") or w.get("position")
            for w in preview["work_experience"]
        ]
        docx_lines = [docx["mehnat_faoliyati"]] + [
            docx.get(f"mehnat_faoliyati_{i}", "") for i in range(2, 9)
        ]
        docx_lines = [x for x in docx_lines if x and x not in ("yo'q", "йўқ")]
        self.assertEqual(len(preview_lines), len(docx_lines))
        for p, d in zip(preview_lines, docx_lines):
            self.assertEqual(p, d)

    def test_legacy_split_payload_reconstructs_current_in_history(self):
        """JS splitCurrentJobFromWorks avval ishni olib tashlagan — backend tiklaydi."""
        raw = {
            "lang": "uz_lat",
            "current_job": "MCHJ rahbari",
            "current_job_year": "2007-yildan:",
            "work_experience": [
                {"year": "2001-2005", "position": "Birinchi ish"},
                {"year": "2005-2007", "position": "Ikkinchi ish"},
            ],
        }
        data = build_malumotnoma_data(raw)
        self.assertEqual(len(data["work_experience"]), 3)
        self.assertTrue(any("MCHJ rahbari" in line for line in data["work_lines"]))

    def test_hozirgacha_token_in_year_field(self):
        raw = {
            "lang": "uz_cyr",
            "work_experience": [{"year": "2015-hozirgacha", "position": "test"}],
        }
        data = build_malumotnoma_data(raw)
        self.assertEqual(data["current_job"], "test")
        self.assertIn("йилдан", data["current_job_year"])
        self.assertEqual(len(data["work_lines"]), 1)
        self.assertIn("ҳ.в", data["work_lines"][0])

    def test_employment_history_alias(self):
        raw = {
            "employment_history": [{"from": "2010", "to": "2014", "position": "Eski"}],
        }
        data = build_malumotnoma_data(raw)
        self.assertEqual(len(data["work_lines"]), 1)
        self.assertIn("Eski", data["work_lines"][0])

    def test_no_current_job_top_empty_mehnat_yoq(self):
        raw = {
            "lang": "uz_lat",
            "current_job": "yo'q",
            "work_experience": [{"year": "1988-1991", "position": "Aspirant"}],
        }
        data = build_malumotnoma_data(raw)
        self.assertEqual(data["current_job"], "")
        self.assertEqual(data["current_job_year"], "")
        self.assertEqual(len(data["work_lines"]), 1)
        preview = build_obyektivka_render_context(raw)
        self.assertEqual(preview["current_job"], "")
        self.assertEqual(len(preview["work_experience"]), 1)

    def test_empty_work_shows_yoq_in_docx_not_top(self):
        raw = {"lang": "uz_lat", "work_experience": [{"position": "yo'q"}]}
        data = build_malumotnoma_data(raw)
        self.assertEqual(data["current_job"], "")
        self.assertEqual(data["work_lines"], [])
        docx = build_placeholder_context(raw)
        self.assertEqual(docx["hozirgi_ish"], "")
        self.assertEqual(docx["mehnat_faoliyati"], "yo'q")

    def test_past_jobs_only_no_top_current(self):
        raw = {
            "lang": "uz_lat",
            "work_experience": [{"year": "2001-2005", "position": "Birinchi ish"}],
        }
        data = build_malumotnoma_data(raw)
        self.assertEqual(data["current_job"], "")
        self.assertEqual(len(data["work_lines"]), 1)


class TestCurrentJobCompat(unittest.TestCase):
    def test_present_token(self):
        from features.obyektivka.current_job import is_present_year_token

        self.assertTrue(is_present_year_token("h.v"))
        self.assertTrue(is_present_year_token("hozirgacha"))

    def test_extract_keeps_all_work_items(self):
        from features.obyektivka.current_job import extract_current_job

        job, year, rest = extract_current_job(
            [{"f": "2014", "t": "h.v", "d": "MCHJ rahbari"}],
            lang="uz_lat",
        )
        self.assertEqual(job, "MCHJ rahbari")
        self.assertEqual(year, "2014-yildan:")
        self.assertEqual(len(rest), 1)
        self.assertIn("MCHJ rahbari", rest[0].get("position", ""))


if __name__ == "__main__":
    unittest.main()
