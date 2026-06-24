"""Test data cleanup from SQLite."""
from __future__ import annotations

import unittest

from database.connection import init_db
from database.repositories import payments as payments_repo
from database.repositories import users as users_repo
from shared.test_data_cleanup import purge_all_test_data


class TestTestDataCleanup(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_purge_removes_audit_payment(self):
        users_repo.upsert_user(990001234, username="audit_user", first_name="Audit", last_name="Test")
        pay = payments_repo.create_payment(990001234, payer_name="Audit Payer")
        self.assertIsNotNone(pay)
        pid = int(pay["id"])

        purge_all_test_data()

        self.assertIsNone(payments_repo.get_payment(pid))
        self.assertIsNone(users_repo.get_by_telegram_id(990001234))

    def test_real_payment_survives_purge(self):
        users_repo.upsert_user(8714999123, first_name="Real", last_name="Keeper")
        pay = payments_repo.create_payment(8714999123, payer_name="Real Keeper")
        self.assertIsNotNone(pay)
        pid = int(pay["id"])

        purge_all_test_data()

        self.assertIsNotNone(users_repo.get_by_telegram_id(8714999123))
        self.assertIsNotNone(payments_repo.get_payment(pid))


if __name__ == "__main__":
    unittest.main()
