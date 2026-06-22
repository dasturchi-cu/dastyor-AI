"""Admin dashboard text builder."""
from __future__ import annotations

import unittest

from features.admin.dashboard import _feed_line, build_dashboard_text


class TestAdminDashboard(unittest.TestCase):
    def test_feed_line_cv(self):
        line = _feed_line({"event_type": "cv", "actor_name": "Bekzod"})
        self.assertIn("Bekzod", line)
        self.assertIn("CV", line)

    def test_dashboard_contains_blocks(self):
        text = build_dashboard_text(
            {
                "users_count": 100,
                "pending_payments": 3,
                "approved_payments": 45,
                "rejected_payments": 2,
                "cv_total": 43,
                "obyektivka_total": 57,
                "revenue_uzs": 359955,
                "active_users": 18,
                "paid_users": 15,
                "conversion_pct": 15.0,
                "new_users_today": 34,
                "cv_today": 17,
                "obyektivka_today": 26,
                "revenue_today_uzs": 145000,
                "top_users": [{"username": "ali", "approved_count": 12}],
                "feed": [{"event_type": "payment", "actor_name": "Jasur"}],
            },
            updated_at="21:00:00",
        )
        self.assertIn("ADMIN DASHBOARD", text)
        self.assertIn("JONLI TA'MINOT", text)
        self.assertIn("KONVERSIYA", text)
        self.assertIn("359,955", text)
        self.assertIn("Foydalanuvchilar", text)
        self.assertIn("Tasdiqlangan", text)


if __name__ == "__main__":
    unittest.main()
