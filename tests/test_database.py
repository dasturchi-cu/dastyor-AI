"""SQLite auto-init, inspection, and admin db-info endpoint."""
from __future__ import annotations

import unittest

from database.connection import initialize_database
from database.inspect import get_database_info
from database.repositories import users as users_repo
from database.verify import REQUIRED_TABLES, verify_schema


class TestDatabaseInit(unittest.TestCase):
    def test_initialize_database_creates_and_verifies(self) -> None:
        report = initialize_database()
        self.assertTrue(report["ok"], report.get("errors"))
        for table in REQUIRED_TABLES:
            self.assertTrue(report["tables"].get(table), f"missing table: {table}")
        self.assertTrue(report.get("queries_ok"))
        self.assertEqual(report["integrity"], "ok")

    def test_inspect_shows_tables_and_counts(self) -> None:
        initialize_database()
        users_repo.upsert_user(999_888_777, username="db_test", first_name="DB")
        info = get_database_info()
        self.assertTrue(info["file_exists"])
        self.assertGreater(info["totals"]["tables"], 0)
        self.assertIn("users", info["row_counts"])
        self.assertGreaterEqual(info["row_counts"]["users"], 1)
        self.assertGreater(len(info["indexes"]), 0)
        self.assertIn("total_bytes", info["size"])

    def test_user_survives_reopen_connection(self) -> None:
        """User row must persist after simulated process restart (new connection)."""
        from database.connection import _local

        tid = 999_777_001
        users_repo.upsert_user(tid, username="persist_test", first_name="Persist")
        if getattr(_local, "conn", None) is not None:
            _local.conn.close()
            _local.conn = None
        row = users_repo.get_by_telegram_id(tid)
        self.assertIsNotNone(row)
        self.assertEqual(row.get("username"), "persist_test")

    def test_admin_db_info_endpoint(self) -> None:
        from fastapi.testclient import TestClient

        from backend.server_app import create_webhook_app
        from config.settings import settings

        initialize_database()
        app = create_webhook_app()
        client = TestClient(app)

        res = client.get("/admin/db-info")
        self.assertEqual(res.status_code, 403)

        secret = settings.webhook_secret
        self.assertTrue(secret, "WEBHOOK_SECRET or BOT_TOKEN required for test")
        res = client.get("/admin/db-info", headers={"X-Admin-Secret": secret})
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertTrue(data.get("file_exists"))
        self.assertIn("users", data.get("row_counts", {}))
        self.assertIn("indexes", data)


if __name__ == "__main__":
    unittest.main()
