"""Admin package sales GROUP BY stats."""
from __future__ import annotations

import unittest

from database.connection import get_connection, init_db
from database.repositories import admin_stats as stats_repo
from database.repositories import payments as payments_repo
from database.repositories import users as users_repo
from features.admin.formatters import build_statistics_text


class TestPackageSalesStats(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        init_db()

    def setUp(self) -> None:
        self.tid = 9_900_231
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM payments WHERE user_id IN (SELECT id FROM users WHERE telegram_id = ?)",
                (self.tid,),
            )
            conn.execute("DELETE FROM users WHERE telegram_id = ?", (self.tid,))
            conn.commit()
        users_repo.upsert_user(self.tid, first_name="PackStats")
        # Avoid promo bonus skewing unrelated asserts
        with get_connection() as conn:
            conn.execute(
                "UPDATE users SET pay_promo_expires_at = NULL WHERE telegram_id = ?",
                (self.tid,),
            )
            conn.commit()

    def test_group_by_package_id(self) -> None:
        p3 = payments_repo.create_payment(
            self.tid, payer_name="A", document_type="cv", package_id="pack3"
        )
        p1 = payments_repo.create_payment(
            self.tid, payer_name="B", document_type="cv", package_id="pack1"
        )
        payments_repo.approve_atomic(int(p3["id"]), admin_note="t")
        payments_repo.approve_atomic(int(p1["id"]), admin_note="t")

        rows = stats_repo.package_sales_stats()
        by_id = {str(r["package_id"]): r for r in rows}
        self.assertIn("pack3", by_id)
        self.assertGreaterEqual(int(by_id["pack3"]["sales"]), 1)
        self.assertIn("pack1", by_id)

        snap = stats_repo.dashboard_snapshot()
        text = build_statistics_text(snap)
        self.assertIn("PAKET SAVDOSI", text)
        self.assertIn("3 hujjat", text)


if __name__ == "__main__":
    unittest.main()
