"""Package credits + promo bonus approval."""
from __future__ import annotations

import unittest

from database.connection import init_db
from database.repositories import payments as payments_repo
from database.repositories import users as users_repo


class TestPackageApprove(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        init_db()

    def _reset_user(self, tid: int, first_name: str) -> None:
        from database.connection import get_connection

        with get_connection() as conn:
            conn.execute(
                "DELETE FROM payments WHERE user_id IN (SELECT id FROM users WHERE telegram_id = ?)",
                (tid,),
            )
            conn.execute("DELETE FROM users WHERE telegram_id = ?", (tid,))
            conn.commit()
        users_repo.upsert_user(tid, first_name=first_name)
        with get_connection() as conn:
            conn.execute(
                "UPDATE users SET credits = 0, pay_promo_expires_at = NULL WHERE telegram_id = ?",
                (tid,),
            )
            conn.commit()

    def test_signup_starts_with_zero_credits(self) -> None:
        tid = 880011001
        self._reset_user(tid, "Zero")
        self.assertEqual(users_repo.get_credits(tid), 0)

    def test_pack3_grants_three_credits(self) -> None:
        tid = 880011002
        self._reset_user(tid, "Pack3")
        pay = payments_repo.create_payment(
            tid, payer_name="Pack3", document_type="cv", package_id="pack3"
        )
        self.assertIsNotNone(pay)
        self.assertEqual(int(pay["amount"]), 14999)
        self.assertEqual(int(pay["credits_granted"]), 3)
        self.assertEqual(pay["package_id"], "pack3")

        result = payments_repo.approve_atomic(int(pay["id"]), admin_note="test")
        self.assertIsNotNone(result)
        self.assertEqual(users_repo.get_credits(tid), 3)
        self.assertEqual(int(result.get("credits_granted") or 0), 3)

    def test_promo_adds_one_extra(self) -> None:
        tid = 880011003
        self._reset_user(tid, "Promo")
        # Re-enable promo window after reset
        promo = users_repo.ensure_pay_promo(tid)
        self.assertTrue(promo.get("active"))

        pay = payments_repo.create_payment(
            tid, payer_name="Promo", document_type="cv", package_id="pack1"
        )
        result = payments_repo.approve_atomic(int(pay["id"]))
        self.assertIsNotNone(result)
        # 1 package + 1 promo
        self.assertEqual(users_repo.get_credits(tid), 2)
        self.assertEqual(int(result.get("promo_bonus_granted") or 0), 1)


if __name__ == "__main__":
    unittest.main()
