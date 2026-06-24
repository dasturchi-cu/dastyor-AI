"""AI quota monitoring tests."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from features.ai.routing.quota import reset_quota_monitor


class TestQuotaMonitor(unittest.TestCase):
    def setUp(self):
        os.environ["AI_QUOTA_DAILY_GEMINI"] = "100"
        os.environ["GEMINI_API_KEY"] = "test-key"
        reset_quota_monitor()

    def tearDown(self):
        reset_quota_monitor()

    @patch("database.repositories.ai_quota.upsert_state")
    @patch("database.repositories.ai_quota.insert_history")
    def test_success_increments_usage(self, _hist, _upsert):
        qm = reset_quota_monitor()
        qm.record_success("gemini", 1, "gemini-2.5-flash")
        g1 = next(r for r in qm.list_all() if r["provider"] == "gemini" and r["key_index"] == 1)
        self.assertEqual(g1["requests_used"], 1)
        self.assertEqual(g1["status"], "ACTIVE")
        self.assertLess(g1["quota_percent"], 100.0)

    @patch("database.repositories.ai_quota.upsert_state")
    @patch("database.repositories.ai_quota.insert_history")
    def test_quota_exhausted_then_reset(self, _hist, _upsert):
        qm = reset_quota_monitor()
        qm.record_quota_exhausted("gemini", 1, "gemini-2.5-flash")
        g1 = next(r for r in qm.list_all() if r["provider"] == "gemini" and r["key_index"] == 1)
        self.assertEqual(g1["status"], "EXHAUSTED")
        self.assertEqual(g1["quota_percent"], 0.0)
        self.assertEqual(g1["requests_remaining"], 0)

        qm.record_success("gemini", 1, "gemini-2.5-flash")
        g1 = next(r for r in qm.list_all() if r["provider"] == "gemini" and r["key_index"] == 1)
        self.assertEqual(g1["status"], "ACTIVE")
        self.assertEqual(g1["requests_used"], 1)
        self.assertEqual(g1["quota_percent"], 99.0)
        self.assertIsNotNone(g1["reset_time"])


if __name__ == "__main__":
    unittest.main()
