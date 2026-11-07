"""Ad-link source tracking: /start payload saved once, reported per source."""
from __future__ import annotations

import os
import tempfile
import unittest

os.environ.setdefault("_HUJJATCHI_TEST", "1")


class TestAdSource(unittest.TestCase):
    def setUp(self):
        from database.connection import get_connection, init_db

        init_db()
        self.uids = [990_100_001, 990_100_002, 990_100_003]
        with get_connection() as conn:
            for uid in self.uids:
                conn.execute("DELETE FROM payments WHERE user_id IN (SELECT id FROM users WHERE telegram_id = ?)", (uid,))
                conn.execute("DELETE FROM users WHERE telegram_id = ?", (uid,))

    def tearDown(self):
        from database.connection import get_connection

        with get_connection() as conn:
            for uid in self.uids:
                conn.execute("DELETE FROM payments WHERE user_id IN (SELECT id FROM users WHERE telegram_id = ?)", (uid,))
                conn.execute("DELETE FROM users WHERE telegram_id = ?", (uid,))

    def test_source_kept_from_first_visit_and_reported(self):
        from database.connection import get_connection
        from database.repositories import users as users_repo

        a, b, c = self.uids
        users_repo.upsert_user(a, first_name="A", source="ads_1")
        users_repo.upsert_user(a, first_name="A", source="ads_2")  # later visit must not overwrite
        users_repo.upsert_user(b, first_name="B", source="ads_1")
        users_repo.upsert_user(c, first_name="C")

        self.assertEqual(users_repo.get_by_telegram_id(a)["source"], "ads_1")
        self.assertIsNone(users_repo.get_by_telegram_id(c)["source"])

        uid_a = users_repo.get_by_telegram_id(a)["id"]
        with get_connection() as conn:
            for amount, status in ((14999, "APPROVED"), (7999, "APPROVED"), (19999, "PENDING")):
                conn.execute(
                    "INSERT INTO payments (user_id, payer_name, card_number, amount, status) VALUES (?, 't', '', ?, ?)",
                    (uid_a, amount, status),
                )

        rows = {r["source"]: r for r in users_repo.ad_source_report(30)}
        self.assertEqual(rows["ads_1"]["users"], 2)
        self.assertEqual(rows["ads_1"]["paid_users"], 1)
        self.assertEqual(rows["ads_1"]["revenue_uzs"], 14999 + 7999)
        self.assertNotIn(None, rows)


if __name__ == "__main__":
    unittest.main()
