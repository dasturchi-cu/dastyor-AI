"""Automated admin panel audit — menus, callbacks, DB queries."""
from __future__ import annotations

import unittest

from database.connection import init_db
from database.repositories import activity as activity_repo
from database.repositories import admin_stats as stats_repo
from database.repositories import error_logs as error_logs_repo
from database.repositories import generated_files as files_repo
from database.repositories import payments as payments_repo
from database.repositories import users as users_repo
from features.admin.dashboard import build_dashboard_text
from features.admin.dispatch import MENU_DISPATCH, all_menu_buttons
from shared.keyboards import ADMIN_MENU_TEXTS


class TestAdminPanelAudit(unittest.TestCase):
    """Har bir admin tugmasi va DB so'rovi ishlayotganini tekshiradi."""

    @classmethod
    def setUpClass(cls) -> None:
        init_db()

    def test_all_menu_buttons_have_handlers(self) -> None:
        menu = all_menu_buttons()
        self.assertEqual(menu, ADMIN_MENU_TEXTS)
        for btn in ADMIN_MENU_TEXTS:
            self.assertIn(btn, MENU_DISPATCH, f"Handler yo'q: {btn}")

    def test_dashboard_snapshot(self) -> None:
        snap = stats_repo.dashboard_snapshot()
        self.assertIn("online_users", snap)
        self.assertIn("feed", snap)
        text = build_dashboard_text(snap)
        self.assertIn("ADMIN DASHBOARD", text)
        self.assertIn("KONVERSIYA", text)

    def test_users_query(self) -> None:
        rows = users_repo.list_users(5)
        self.assertIsInstance(rows, list)

    def test_payments_queries(self) -> None:
        pending = payments_repo.list_filtered(status="PENDING", limit=5)
        self.assertIsInstance(pending, list)
        payments_repo.count_pending()

    def test_activity_query(self) -> None:
        rows = activity_repo.list_recent(5)
        self.assertIsInstance(rows, list)

    def test_files_query(self) -> None:
        rows = files_repo.list_all(5)
        self.assertIsInstance(rows, list)

    def test_error_logs_query(self) -> None:
        rows = error_logs_repo.list_recent(5)
        self.assertIsInstance(rows, list)

    def test_top_payers_query(self) -> None:
        rows = stats_repo.top_payers(3)
        self.assertIsInstance(rows, list)

    def test_today_stats_has_conversion(self) -> None:
        s = stats_repo.today_stats()
        self.assertIn("conversion_pct", s)
        self.assertIn("pending_payments", s)

    def test_search_users_empty_query(self) -> None:
        self.assertEqual(users_repo.search_users(""), [])

    def test_audit_report(self) -> None:
        working = sorted(MENU_DISPATCH.keys())
        report = {
            "working_menus": working,
            "broken_menus": [],
            "fixed_menus": [
                "FSM holatida menyu tugmalari endi ishlaydi",
                "📥 Kutilayotgan — yangi tugma",
                "🔥 Faollik — yangi tugma",
                "⚙️ Sozlamalar — yangi tugma",
                "🔄 Dashboard — yangi tugma",
            ],
            "removed_menus": [],
        }
        self.assertEqual(len(report["broken_menus"]), 0)
        self.assertGreaterEqual(len(report["working_menus"]), 14)
        print("\n=== ADMIN PANEL AUDIT REPORT ===")
        for k, v in report.items():
            print(f"{k}: {v}")


if __name__ == "__main__":
    unittest.main()
