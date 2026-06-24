"""AI service pipeline tests (mocked Gemini)."""
from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from features.ai.gemini_client import is_valid_transcription_text
from features.ai.service import (
    extract_cv_data,
    get_missing_cv_fields,
    get_missing_oby_fields,
    map_obyektivka_fields,
    process_text_for_cv,
    process_text_for_obyektivka,
)


class TestTranscriptionValidation(unittest.TestCase):
    def test_rejects_error_messages(self):
        self.assertFalse(is_valid_transcription_text("Audio yuklashda xatolik."))
        self.assertFalse(is_valid_transcription_text(""))
        self.assertFalse(is_valid_transcription_text("[EMPTY]"))

    def test_accepts_real_speech(self):
        self.assertTrue(is_valid_transcription_text("Men Ali Valiyev, Toshkentdanman"))


class TestObyektivkaMapping(unittest.TestCase):
    def test_normalizes_aliases_and_lists(self):
        raw = {
            "full_name": "Karimov Jasur Olimovich",
            "birth_date": "01.01.1990",
            "works": [{"from": "2018", "to": "2024", "work_place": "Maktab"}],
            "relatives": [{"relation": "ota", "name": "Karimov Olim"}],
        }
        out = map_obyektivka_fields(raw)
        self.assertEqual(out["fullname"], "Karimov Jasur Olimovich")
        self.assertEqual(out["birthdate"], "01.01.1990")
        self.assertEqual(out["work_experience"][0]["position"], "Maktab")
        self.assertEqual(out["relatives"][0]["degree"], "ota")
        self.assertEqual(out["party"], "yo'q")

    def test_missing_fields_detected(self):
        data = map_obyektivka_fields({"fullname": "Test User"})
        missing_ids = {m["id"] for m in get_missing_oby_fields(data)}
        self.assertIn("birthdate", missing_ids)
        self.assertIn("work_experience", missing_ids)


class TestCvExtraction(unittest.TestCase):
    @patch("features.ai.service.generate_text_with_fallback", new_callable=AsyncMock)
    def test_extract_cv_parses_fenced_json(self, mock_gen):
        mock_gen.return_value = '```json\n{"fullname": "Ali Valiyev", "phone": "+998901234567"}\n```'

        data = asyncio.run(extract_cv_data("Men Ali Valiyevman"))

        self.assertEqual(data["name"], "Ali Valiyev")
        self.assertEqual(data["phone"], "+998901234567")
        self.assertNotIn("fullname", data)

    @patch("features.ai.service.generate_text_with_fallback", new_callable=AsyncMock)
    def test_extract_cv_rejects_empty_payload(self, mock_gen):
        mock_gen.return_value = '{"name": "", "phone": ""}'
        data = asyncio.run(extract_cv_data("salom"))
        self.assertEqual(data, {})

    @patch("features.ai.service.generate_text_with_fallback", new_callable=AsyncMock)
    def test_process_text_for_cv_pipeline(self, mock_gen):
        mock_gen.return_value = (
            '{"name": "Ali Valiyev", "phone": "+998901234567", "spec": "Dasturchi", '
            '"works": [{"title": "Dev", "company": "ACME"}]}'
        )
        transcript, data, missing = asyncio.run(
            process_text_for_cv("Men Ali Valiyev, +998901234567 raqamida")
        )
        self.assertIn("Ali", transcript)
        self.assertEqual(data["name"], "Ali Valiyev")
        self.assertFalse(any("Ism topilmadi" in m for m in missing))


class TestObyektivkaExtraction(unittest.TestCase):
    @patch("features.ai.service.extract_obyektivka_data", new_callable=AsyncMock)
    def test_process_text_pipeline(self, mock_extract):
        mock_extract.return_value = {
            "fullname": "Karimov Jasur",
            "birthdate": "01.01.1990",
            "birthplace": "Toshkent",
            "nation": "O'zbek",
            "education": "Oliy",
            "graduated": "TATU 2012",
            "specialty": "IT",
            "work_experience": [{"year": "2012-2024", "position": "Dasturchi"}],
            "relatives": [],
        }
        transcript, data, missing = asyncio.run(
            process_text_for_obyektivka("Men Karimov Jasur...")
        )
        self.assertEqual(data["fullname"], "Karimov Jasur")
        self.assertTrue(any(m["id"] == "relatives" for m in missing))


class TestMissingCvFields(unittest.TestCase):
    def test_core_labels(self):
        missing = get_missing_cv_fields({"name": "Ali"})
        self.assertIn("Telefon", missing)
        self.assertIn("Email", missing)


if __name__ == "__main__":
    unittest.main()
