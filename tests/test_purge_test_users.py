"""purge_test_users — audit akkauntlar bazadan o'chiriladi."""
from __future__ import annotations

import unittest

from database.connection import init_db
from database.repositories import users as users_repo


class TestPurgeTestUsers(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_purge_removes_test_keeps_real(self):
        users_repo.upsert_user(990001234, username="audit_user", first_name="Audit", last_name="Test")
        users_repo.upsert_user(8714123163, first_name="Real", last_name="User")
        removed = users_repo.purge_test_users()
        self.assertIn(990001234, removed)
        self.assertIsNone(users_repo.get_by_telegram_id(990001234))
        self.assertIsNotNone(users_repo.get_by_telegram_id(8714123163))


if __name__ == "__main__":
    unittest.main()
