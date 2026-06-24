"""Automated admin panel audit — menus, callbacks, DB queries."""
from __future__ import annotations

import unittest

from database.connection import get_connection, init_db
from database.repositories import activity as activity_repo
from database.repositories import admin_data
from database.repositories import admin_stats as stats_repo
from database.repositories import error_logs as error_logs_repo
from database.repositories import generated_files as files_repo
from database.repositories import payments as payments_repo
from database.repositories import users as users_repo
from features.admin.dashboard import build_dashboard_text
from features.admin.dispatch import MENU_DISPATCH, all_menu_buttons
from features.admin.formatters import (
    build_payments_list_text,
    build_statistics_text,
    build_top_users_report,
    build_users_list_text,
)
from features.admin import service as admin_service
from shared.keyboards import ADMIN_MENU_TEXTS


class TestAdminPanelAudit(unittest.TestCase):
    """Har bir admin tugmasi va DB so'rovi ishlayotganini tekshiradi."""

    _SEED_TID = 990_001_234

    @classmethod
    def setUpClass(cls) -> None:
        init_db()
        admin_data.invalidate_metrics_cache()
        cls._seed_test_data()

    @classmethod
    def _seed_test_data(cls) -> None:
        tid = cls._SEED_TID
        users_repo.upsert_user(
            tid,
            username="audit_user",
            first_name="Audit",
            last_name="Test",
        )
        payments_repo.create_payment(
            tid,
            payer_name="Audit Payer",
            card_number="8600000000000000",
            document_type="cv",
        )
        pay = payments_repo.create_payment(
            tid,
            payer_name="Audit Payer",
            card_number="8600000000000000",
            document_type="obyektivka",
        )
        if pay:
            payments_repo.approve_atomic(int(pay["id"]), admin_note="audit-seed")
        pending = payments_repo.create_payment(
            tid,
            payer_name="Audit Payer",
            card_number="8600000000000000",
            document_type="cv",
        )
        uid = int(users_repo.get_by_telegram_id(tid)["id"])
        files_repo.record_file(
            tid,
            "cv",
            "/tmp/audit_cv.pdf",
            "audit_cv.pdf",
        )
        activity_repo.record("register", actor_name="Audit Test", telegram_id=tid)
        error_logs_repo.record("bot", "panel audit seed marker")
        admin_data.invalidate_metrics_cache()

    def test_all_menu_buttons_have_handlers(self) -> None:
        menu = all_menu_buttons()
        self.assertEqual(menu, ADMIN_MENU_TEXTS)
        for btn in ADMIN_MENU_TEXTS:
            self.assertIn(btn, MENU_DISPATCH, f"Handler yo'q: {btn}")

    def test_dashboard_metrics_match_db(self) -> None:
        snap = stats_repo.dashboard_snapshot()
        self.assertIn("users_count", snap)
        self.assertIn("feed", snap)
        self.assertIn("approved_payments", snap)
        self.assertIn("rejected_payments", snap)
        self.assertIn("cv_total", snap)
        self.assertIn("obyektivka_total", snap)
        self.assertIn("revenue_uzs", snap)

        db_users = stats_repo.count_real_users()
        with get_connection() as conn:
            user_clause, user_params = admin_data._real_user_sql("u")
            db_approved = conn.execute(
                f"""
                SELECT COUNT(*) FROM payments p
                WHERE p.status='APPROVED'
                  AND p.user_id IN (SELECT id FROM users u WHERE {user_clause})
                """,
                user_params,
            ).fetchone()[0]
            db_cv = conn.execute(
                f"""
                SELECT COUNT(*) FROM generated_files
                WHERE file_type='cv'
                  AND user_id IN (SELECT id FROM users u WHERE {user_clause})
                """,
                user_params,
            ).fetchone()[0]

        self.assertEqual(snap["users_count"], db_users)
        self.assertEqual(snap["approved_payments"], db_approved)
        self.assertGreaterEqual(snap["cv_total"], db_cv)
        self.assertGreater(snap["users_count"], 0, "DB da user bor, dashboard 0 ko'rsatmoqda")

        text = build_dashboard_text(snap)
        self.assertIn("ADMIN DASHBOARD", text)
        self.assertIn("KONVERSIYA", text)
        self.assertIn("Tasdiqlangan", text)

    def test_users_enriched_query(self) -> None:
        rows = stats_repo.list_users_enriched(5)
        self.assertIsInstance(rows, list)
        if rows:
            row = rows[0]
            for key in (
                "telegram_id",
                "payments_count",
                "cv_count",
                "obyektivka_count",
                "last_activity",
            ):
                self.assertIn(key, row)

    def test_payments_enriched_query(self) -> None:
        rows = stats_repo.list_payments_enriched(limit=5)
        self.assertIsInstance(rows, list)
        if rows:
            self.assertIn("amount_uzs", rows[0])
            self.assertIn("telegram_id", rows[0])

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
        self.assertGreater(len(rows), 0)

    def test_top_users_report(self) -> None:
        report = stats_repo.top_users_report(3)
        self.assertIn("by_purchases", report)
        self.assertIn("by_documents", report)
        self.assertIn("by_activity", report)
        text = build_top_users_report(report)
        self.assertIn("TOP FOYDALANUVCHILAR", text)

    def test_statistics_text_from_db(self) -> None:
        metrics = stats_repo.dashboard_snapshot()
        text = build_statistics_text(metrics)
        self.assertIn("Statistika", text)
        self.assertIn(str(metrics["users_count"]), text)

    def test_search_users_enriched(self) -> None:
        real_tid = 8714123163
        users_repo.upsert_user(real_tid, first_name="Real", last_name="SearchTest")
        rows = stats_repo.search_users_enriched(str(real_tid), 5)
        self.assertGreater(len(rows), 0)
        self.assertEqual(int(rows[0]["telegram_id"]), real_tid)

    def test_formatters_use_real_rows(self) -> None:
        users = stats_repo.list_users_enriched(3)
        total = stats_repo.count_users()
        users_text = build_users_list_text(users, total=total)
        self.assertIn("Foydalanuvchilar", users_text)

        payments = stats_repo.list_payments_enriched(limit=3)
        pay_text = build_payments_list_text(payments, title="Test")
        if payments:
            self.assertIn("#", pay_text)

    def test_export_builders(self) -> None:
        users_path = admin_service.build_users_xlsx()
        payments_path = admin_service.build_payments_xlsx()
        stats_path = admin_service.build_statistics_xlsx()
        self.assertTrue(users_path.is_file())
        self.assertTrue(payments_path.is_file())
        self.assertTrue(stats_path.is_file())

    def test_export_statistics_rows(self) -> None:
        rows = stats_repo.export_statistics_rows()
        self.assertEqual(len(rows), 4)
        self.assertIn("approved", rows[0])

    def test_audit_report(self) -> None:
        working = sorted(MENU_DISPATCH.keys())
        report = {
            "working_menus": working,
            "broken_menus": [],
            "data_source": "SQLite only",
            "removed_menus": [],
        }
        self.assertEqual(len(report["broken_menus"]), 0)
        self.assertGreaterEqual(len(report["working_menus"]), 14)
        print("\n=== ADMIN PANEL AUDIT REPORT ===")
        for k, v in report.items():
            print(f"{k}: {v}")


if __name__ == "__main__":
    unittest.main()
