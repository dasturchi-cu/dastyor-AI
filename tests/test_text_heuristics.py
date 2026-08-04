"""Heuristic text extraction tests."""
from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from features.ai.service import (
    count_cv_populated_fields,
    count_oby_populated_fields,
    cv_fill_is_acceptable,
    cv_fill_rejection_reason,
    oby_fill_is_acceptable,
    process_text_for_cv,
    process_text_for_obyektivka,
)
from features.ai.text_heuristics import parse_cv_facts, parse_obyektivka_facts

SAMPLE = (
    "Men Ali Valiyevman, Toshkent shahriman. Telefon +998901234567, "
    "email ali@gmail.com. Python dasturchiman. 2020-2024 TDYU da kompyuter fanlari "
    "bo'yicha o'qidim. 2024-yildan beri IT kompaniyada ishlayman."
)

STRUCTURED_CV = """\
Full name: Karimov Jasur Vali o'g'li
Birth date: 15.03.1995
Birth place: Toshkent shahri
Education: TDYU, 2013-2017, Kompyuter fanlari
Specialty: Dasturiy ta'minot muhandisi
Work experience: 2017-2024 — IT kompaniya, Backend dasturchi
Skills: Python, FastAPI, PostgreSQL, Docker
Languages: O'zbek (ona tili), Rus (erkin), Ingliz (o'rta)
Achievements: Respublika olimpiadasi g'olibi
"""


class TestTextHeuristics(unittest.TestCase):
    def test_parse_cv_sample(self):
        data = parse_cv_facts(SAMPLE)
        self.assertEqual(data["name"], "Ali Valiyev")
        self.assertEqual(data["phone"], "+998901234567")
        self.assertEqual(data["email"], "ali@gmail.com")
        self.assertIn("Toshkent", data["loc"])
        self.assertTrue(data.get("education_list"))
        self.assertTrue(data.get("works"))

    def test_parse_obyektivka_from_cv_sample(self):
        data = parse_obyektivka_facts(SAMPLE)
        self.assertEqual(data["fullname"], "Ali Valiyev")
        self.assertTrue(data.get("work_experience"))

    def test_cv_fill_acceptable_requires_name_and_one_bonus_field(self):
        self.assertFalse(cv_fill_is_acceptable({"about": "Men Ali"}, []))
        self.assertFalse(cv_fill_is_acceptable({}, []))
        self.assertFalse(
            cv_fill_is_acceptable({"name": "Ali Valiyev", "phone": "+998901234567"}, [])
        )
        # A single bonus field (e.g. profession) is enough — avoids over-rejecting
        # brief-but-useful voice/text input from the flagship AI-fill feature.
        self.assertTrue(
            cv_fill_is_acceptable({"name": "Ali Valiyev", "spec": "Sotuvchi"}, [])
        )
        self.assertTrue(
            cv_fill_is_acceptable(
                {
                    "name": "Ali Valiyev",
                    "skills": "Python, FastAPI",
                    "spec": "Dasturchi",
                },
                [],
            )
        )
        self.assertEqual(cv_fill_rejection_reason({"phone": "+998"}), "Ism topilmadi.")

    def test_parse_structured_cv_sample(self):
        data = parse_cv_facts(STRUCTURED_CV)
        self.assertIn("Karimov", data["name"])
        self.assertTrue(data.get("education_list"))
        self.assertTrue(data.get("works"))
        self.assertTrue(data.get("skills"))
        self.assertTrue(data.get("languages_list"))
        self.assertTrue(data.get("spec"))
        self.assertTrue(cv_fill_is_acceptable(data, []))

    @patch("features.ai.service.generate_text_with_fallback", new_callable=AsyncMock)
    def test_process_structured_cv_without_ai(self, mock_gen):
        mock_gen.return_value = '{"name": "", "phone": ""}'
        transcript, data, missing = asyncio.run(process_text_for_cv(STRUCTURED_CV))
        self.assertIn("Karimov", data.get("name", ""))
        self.assertTrue(cv_fill_is_acceptable(data, missing))
        self.assertFalse(any("Ism topilmadi" in m for m in missing))

    def test_populated_field_counts(self):
        data = parse_cv_facts(SAMPLE)
        self.assertGreaterEqual(count_cv_populated_fields(data), 4)
        oby = parse_obyektivka_facts(SAMPLE)
        self.assertGreaterEqual(count_oby_populated_fields(oby), 1)


class TestTextPipelineWithoutAi(unittest.TestCase):
    @patch("features.ai.service.generate_text_with_fallback", new_callable=AsyncMock)
    def test_process_cv_text_uses_heuristics_when_ai_empty(self, mock_gen):
        mock_gen.return_value = '{"name": "", "phone": ""}'
        transcript, data, missing = asyncio.run(process_text_for_cv(SAMPLE))
        self.assertIn("Ali", transcript)
        self.assertEqual(data.get("name"), "Ali Valiyev")
        self.assertTrue(cv_fill_is_acceptable(data, missing))

    @patch("features.ai.service.extract_obyektivka_data", new_callable=AsyncMock)
    def test_process_oby_text_uses_heuristics_when_ai_empty(self, mock_extract):
        mock_extract.return_value = {}
        transcript, data, missing = asyncio.run(process_text_for_obyektivka(SAMPLE))
        self.assertEqual(data.get("fullname"), "Ali Valiyev")
        self.assertTrue(oby_fill_is_acceptable(data))
        self.assertTrue(isinstance(missing, list))


if __name__ == "__main__":
    unittest.main()
