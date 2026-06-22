"""Admin dashboard text builder."""
from __future__ import annotations

import unittest

from features.admin.dashboard import build_dashboard_text, _feed_line


class TestAdminDashboard(unittest.TestCase):
    def test_feed_line_cv(self):
        line = _feed_line({"event_type": "cv", "actor_name": "Bekzod"})
        self.assertIn("Bekzod", line)
        self.assertIn("CV", line)

    def test_dashboard_contains_blocks(self):
        text = build_dashboard_text(
            {
                "online_users": 12,
                "today_users": 34,
                "pending_payments": 3,
                "cv": 17,
                "obyektivka": 26,
                "revenue_uzs": 145000,
                "active_users": 18,
                "inactive_users": 212,
                "total_users": 100,
                "paid_users": 15,
                "conversion_pct": 15.0,
                "cv_total": 43,
                "obyektivka_total": 57,
                "top_users": [{"username": "ali", "approved_count": 12}],
                "feed": [{"event_type": "payment", "actor_name": "Jasur"}],
            },
            updated_at="21:00:00",
        )
        self.assertIn("ADMIN DASHBOARD", text)
        self.assertIn("JONLI TA'MINOT", text)
        self.assertIn("KONVERSIYA", text)
        self.assertIn("TOP FOYDALANUVCHILAR", text)
        self.assertIn("145,000", text)


if __name__ == "__main__":
    unittest.main()
