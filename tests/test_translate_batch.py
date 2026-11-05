"""translate_strings_batch: one AI request per chunk, safe per-string fallback."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from features.ai import gemini_client as gc


class TestTranslateBatch(unittest.IsolatedAsyncioTestCase):
    async def test_many_strings_use_single_request(self):
        prompts: list[str] = []

        async def fake(prompt: str, **_):
            prompts.append(prompt)
            items = json.loads(prompt[prompt.index("[") :])
            return "```json\n" + json.dumps([f"EN:{x}" for x in items]) + "\n```"

        texts = ["Bosh hisobchi", "yo'q", "Toshkent davlat universiteti", "Oliy"]
        with patch.object(gc, "generate_text_with_fallback", side_effect=fake):
            out = await gc.translate_strings_batch(texts, "uz_en")

        self.assertEqual(len(prompts), 1)
        self.assertEqual(
            out, ["EN:Bosh hisobchi", "none", "EN:Toshkent davlat universiteti", "EN:Oliy"]
        )

    async def test_size_mismatch_falls_back_per_string(self):
        calls = {"batch": 0, "single": 0}

        async def fake(prompt: str, **_):
            if "JSON array" in prompt:
                calls["batch"] += 1
                return '["only one"]'
            calls["single"] += 1
            return "EN:" + prompt.rsplit("\n\n", 1)[-1]

        texts = ["Bosh hisobchi", "Oliy ma'lumotli"]
        with patch.object(gc, "generate_text_with_fallback", side_effect=fake):
            out = await gc.translate_strings_batch(texts, "uz_en")

        self.assertEqual(calls, {"batch": 1, "single": 2})
        self.assertEqual(out, ["EN:Bosh hisobchi", "EN:Oliy ma'lumotli"])

    async def test_garbage_item_keeps_source(self):
        async def fake(prompt: str, **_):
            return json.dumps(["Chief Accountant", "Please provide the text to translate"])

        texts = ["Bosh hisobchi", "Oliy"]
        with patch.object(gc, "generate_text_with_fallback", side_effect=fake):
            out = await gc.translate_strings_batch(texts, "uz_en")

        self.assertEqual(out, ["Chief Accountant", "Oliy"])

    def test_chunking_respects_limits(self):
        texts = ["x" * 100] * 95
        chunks = gc._chunk_for_batch(list(range(95)), texts)
        self.assertTrue(all(len(c) <= gc._BATCH_TRANSLATE_MAX_ITEMS for c in chunks))
        self.assertEqual(sorted(i for c in chunks for i in c), list(range(95)))


if __name__ == "__main__":
    unittest.main()
