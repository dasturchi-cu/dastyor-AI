"""Noise error log filter."""
from __future__ import annotations

import unittest

from database.connection import init_db
from database.repositories import error_logs as error_logs_repo
from shared.error_log import is_noise_error, purge_noise_error_logs, record_error


class TestErrorLogFilter(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_chat_not_found_is_noise(self):
        self.assertTrue(
            is_noise_error(
                "payment",
                "Admin callback #128: Telegram server says - Bad Request: chat not found",
            )
        )

    def test_audit_test_is_noise(self):
        self.assertTrue(is_noise_error("bot", "audit test error"))

    def test_real_error_not_noise(self):
        self.assertFalse(is_noise_error("pdf", "LibreOffice conversion failed"))

    def test_record_skips_noise(self):
        before = len(error_logs_repo.list_recent(50))
        record_error("payment", "Admin callback #1: chat not found")
        record_error("pdf", "unique real failure xyz123")
        rows = [r for r in error_logs_repo.list_recent(50) if "xyz123" in str(r.get("message"))]
        self.assertEqual(len(rows), 1)

    def test_purge_removes_noise(self):
        error_logs_repo.record("bot", "audit test error")
        error_logs_repo.record("payment", "Admin callback #9: chat not found")
        removed = purge_noise_error_logs()
        self.assertGreaterEqual(removed, 2)
        rows = error_logs_repo.list_recent(50)
        for row in rows:
            blob = str(row.get("message") or "").lower()
            self.assertNotIn("audit test error", blob)
            self.assertNotIn("chat not found", blob)


if __name__ == "__main__":
    unittest.main()
