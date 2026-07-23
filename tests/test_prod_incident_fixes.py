"""Regression tests for production incident fixes (health / webhook / AI content)."""
from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from features.ai.routing.adapters import _message_content_to_text


class TestMessageContentNormalize(unittest.TestCase):
    def test_string(self) -> None:
        self.assertEqual(_message_content_to_text("  OK  "), "OK")

    def test_list_of_parts(self) -> None:
        content = [{"type": "text", "text": "Hel"}, {"type": "text", "text": "lo"}]
        self.assertEqual(_message_content_to_text(content), "Hello")

    def test_none(self) -> None:
        self.assertEqual(_message_content_to_text(None), "")


class TestQuickHealth(unittest.TestCase):
    def test_quick_health_ok(self) -> None:
        from database.connection import initialize_database
        from database.verify import quick_health_check

        initialize_database()
        report = quick_health_check()
        self.assertTrue(report["ok"], report)


class TestWebhookBenignErrors(unittest.TestCase):
    def test_blocked_user_is_benign(self) -> None:
        from backend.routers.tg_update import _is_benign_delivery_error

        self.assertTrue(
            _is_benign_delivery_error(
                RuntimeError("Telegram server says - Forbidden: bot was blocked by the user")
            )
        )


class TestQuotaSnapshotNoHistory(unittest.TestCase):
    def test_snapshot_skips_history_insert(self) -> None:
        from features.ai.routing.quota import QuotaMonitor, QuotaState

        mon = QuotaMonitor()
        mon._loaded = True
        mon._states[("gemini", 1)] = QuotaState(
            provider="gemini", key_index=1, model="m", daily_limit=10
        )
        with patch("features.ai.routing.quota.os.getenv", return_value=""):
            with patch("database.repositories.ai_quota.upsert_state") as up:
                with patch("database.repositories.ai_quota.insert_history") as hist:
                    mon.snapshot_all()
                    self.assertTrue(up.called)
                    self.assertFalse(hist.called)


if __name__ == "__main__":
    unittest.main()
