"""Admin AI status text tests."""
from __future__ import annotations

import unittest

from features.admin.ai_dashboard import build_ai_status_text


class TestAiDashboardText(unittest.TestCase):
    def test_build_contains_provider_and_model(self):
        snap = {
            "active": {
                "provider": "gemini",
                "key_index": 3,
                "model": "gemini-2.5-flash",
                "status": "ACTIVE",
                "health_pct": 98.0,
            },
            "analytics": {
                "total_requests_today": 42,
                "failure_rate_pct": 2.5,
                "total_tokens_today": 1000,
                "estimated_cost_usd": 0.01,
            },
            "providers": [],
            "cooldowns": [],
        }
        text = build_ai_status_text(snap, compact=True)
        self.assertIn("GEMINI", text)
        self.assertIn("gemini-2.5-flash", text)
        self.assertIn("#3", text)
        self.assertIn("ACTIVE", text)


if __name__ == "__main__":
    unittest.main()
