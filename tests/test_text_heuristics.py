"""Heuristic text extraction tests."""
from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from features.ai.service import cv_fill_is_acceptable, oby_fill_is_acceptable, process_text_for_cv, process_text_for_obyektivka
from features.ai.text_heuristics import parse_cv_facts, parse_obyektivka_facts

SAMPLE = (
    "Men Ali Valiyevman, Toshkent shahriman. Telefon +998901234567, "
    "email ali@gmail.com. Python dasturchiman. 2020-2024 TDYU da kompyuter fanlari "
    "bo'yicha o'qidim. 2024-yildan beri IT kompaniyada ishlayman."
)


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

    def test_cv_fill_acceptable_requires_name_and_more(self):
        self.assertFalse(cv_fill_is_acceptable({"about": "Men Ali"}, ["F.I.SH"]))
        self.assertTrue(
            cv_fill_is_acceptable(
                {"name": "Ali Valiyev", "phone": "+998901234567"},
                ["Email"],
            )
        )


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
