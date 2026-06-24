"""Database path must stay on the persistent DATA_DIR volume."""
from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


class TestDbPathResolution(unittest.TestCase):
    def _resolve_db_path(self, **env: str) -> tuple[str, str]:
        merged = os.environ.copy()
        for key in ("DB_PATH", "DATA_DIR", "RAILWAY_VOLUME_MOUNT_PATH"):
            merged.pop(key, None)
        merged.update(env)
        merged["_HUJJATCHI_TEST"] = "1"
        code = """
from config.settings import DB_PATH, DATA_DIR
print(f"{DB_PATH.resolve()}|{DATA_DIR.resolve()}")
"""
        out = subprocess.check_output(
            [sys.executable, "-c", code],
            env=merged,
            cwd=str(Path(__file__).resolve().parent.parent),
            text=True,
        ).strip()
        db_path, data_dir = out.split("|", 1)
        return db_path, data_dir

    def test_local_db_path_ignores_absolute_data_outside_project(self) -> None:
        db_path, data_dir = self._resolve_db_path(DB_PATH="/data/app.db")
        self.assertTrue(db_path.endswith("data\\app.db") or db_path.endswith("data/app.db"))
        self.assertIn("hujjatchi_ai_bot", db_path)
        self.assertIn("data", data_dir)

    def test_explicit_data_dir_honors_db_path(self) -> None:
        db_path, _ = self._resolve_db_path(DATA_DIR="/data", DB_PATH="/data/app.db")
        self.assertTrue(db_path.replace("\\", "/").endswith("/data/app.db"))


if __name__ == "__main__":
    unittest.main()
