"""Reliable AI utility tests (no live Gemini calls)."""
from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock

from features.ai.reliable import (
    cv_extract_has_content,
    normalize_cv_data,
    oby_extract_has_content,
    parse_json_object,
    response_text_or_empty,
    retry_ai,
)
from shared.ai_errors import AiQuotaError, is_transient_ai_error


class TestParseJsonObject(unittest.TestCase):
    def test_plain_json(self):
        out = parse_json_object('{"name": "Ali Valiyev", "phone": "+998901234567"}')
        self.assertEqual(out["name"], "Ali Valiyev")

    def test_markdown_fence(self):
        raw = """```json
{"fullname": "Karimov Jasur"}
```"""
        out = parse_json_object(raw)
        self.assertEqual(out["fullname"], "Karimov Jasur")

    def test_trailing_comma(self):
        out = parse_json_object('{"name": "Test", "works": [],}')
        self.assertEqual(out["name"], "Test")

    def test_prefix_suffix_noise(self):
        out = parse_json_object('Natija:\n{"party": "yo\'q"}\nTugadi.')
        self.assertEqual(out["party"], "yo'q")

    def test_invalid_returns_none(self):
        self.assertIsNone(parse_json_object("not json at all"))
        self.assertIsNone(parse_json_object(""))
        self.assertIsNone(parse_json_object("[1,2,3]"))


class TestContentValidators(unittest.TestCase):
    def test_cv_requires_meaningful_field(self):
        self.assertFalse(cv_extract_has_content({}))
        self.assertFalse(cv_extract_has_content({"name": "", "phone": "yo'q"}))
        self.assertTrue(cv_extract_has_content({"name": "Ali Valiyev"}))
        self.assertTrue(cv_extract_has_content({"works": [{"title": "Dev"}]}))

    def test_oby_requires_meaningful_field(self):
        self.assertFalse(oby_extract_has_content({}))
        self.assertTrue(oby_extract_has_content({"fullname": "Ali Valiyev"}))
        self.assertTrue(
            oby_extract_has_content(
                {"work_experience": [{"year": "2020-2024", "position": "Muhandis"}]}
            )
        )


class TestNormalizeCvData(unittest.TestCase):
    def test_aliases_and_lists(self):
        raw = {
            "fullname": "Ali Valiyev",
            "location": "Toshkent",
            "work_experience": [
                {"position": "Backend", "employer": "ACME", "from": "2022", "to": "2024"}
            ],
            "education": [{"degree": "IT", "school": "TATU", "year": "2020"}],
        }
        out = normalize_cv_data(raw)
        self.assertEqual(out["name"], "Ali Valiyev")
        self.assertEqual(out["loc"], "Toshkent")
        self.assertEqual(out["works"][0]["title"], "Backend")
        self.assertEqual(out["education_list"][0]["company"], "TATU")


class TestResponseText(unittest.TestCase):
    def test_empty_when_missing(self):
        self.assertEqual(response_text_or_empty(None), "")

    def test_reads_text_attr(self):
        class R:
            text = "  Salom  "

        self.assertEqual(response_text_or_empty(R()), "Salom")


class TestRetryAi(unittest.TestCase):
    def test_retries_transient_then_succeeds(self):
        calls = {"n": 0}

        async def factory():
            calls["n"] += 1
            if calls["n"] < 2:
                raise TimeoutError("deadline")
            return "ok"

        result = asyncio.run(retry_ai(factory, attempts=3, base_delay=0))
        self.assertEqual(result, "ok")
        self.assertEqual(calls["n"], 2)

    def test_quota_not_retried(self):
        async def factory():
            raise AiQuotaError("quota")

        with self.assertRaises(AiQuotaError):
            asyncio.run(retry_ai(factory, attempts=3, base_delay=0))


class TestTransientErrors(unittest.TestCase):
    def test_detects_timeout(self):
        self.assertTrue(is_transient_ai_error(TimeoutError()))

    def test_ignores_quota(self):
        self.assertFalse(is_transient_ai_error(AiQuotaError("quota")))


if __name__ == "__main__":
    unittest.main()
