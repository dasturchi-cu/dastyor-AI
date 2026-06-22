"""Database integrity and schema verification."""
from __future__ import annotations

import sqlite3
from typing import Any

from config.settings import settings

REQUIRED_TABLES = (
    "users",
    "payments",
    "documents",
    "cv_documents",
    "obyektivka_documents",
    "support_messages",
    "admin_logs",
    "settings",
    "cv_data",
    "obyektivka_data",
    "ai_sessions",
    "activity_events",
    "error_logs",
)

REQUIRED_INDEXES = (
    "idx_users_telegram",
    "idx_payments_user",
    "idx_payments_status",
    "idx_payments_number",
    "idx_payments_created",
    "idx_cv_documents_user",
    "idx_oby_documents_user",
    "idx_support_user",
    "idx_admin_logs_created",
)

REQUIRED_VIEWS = ("generated_files",)


def check_db_integrity() -> tuple[bool, str]:
    with sqlite3.connect(settings.db_path) as conn:
        row = conn.execute("PRAGMA integrity_check").fetchone()
    msg = str(row[0]) if row else "unknown"
    return msg == "ok", msg


def verify_schema() -> dict[str, Any]:
    """Return verification report for startup / health checks."""
    report: dict[str, Any] = {
        "ok": True,
        "db_path": str(settings.db_path),
        "tables": {},
        "indexes": {},
        "views": {},
        "integrity": "unknown",
        "errors": [],
    }

    if not settings.db_path.is_file():
        report["ok"] = False
        report["errors"].append(f"Database file missing: {settings.db_path}")
        return report

    ok, msg = check_db_integrity()
    report["integrity"] = msg
    if not ok:
        report["ok"] = False
        report["errors"].append(f"integrity_check failed: {msg}")

    with sqlite3.connect(settings.db_path) as conn:
        existing_tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        existing_indexes = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
        }
        existing_views = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'view'"
            ).fetchall()
        }

        for name in REQUIRED_TABLES:
            present = name in existing_tables
            report["tables"][name] = present
            if not present:
                report["ok"] = False
                report["errors"].append(f"Missing table: {name}")

        for name in REQUIRED_INDEXES:
            present = name in existing_indexes
            report["indexes"][name] = present
            if not present:
                report["ok"] = False
                report["errors"].append(f"Missing index: {name}")

        for name in REQUIRED_VIEWS:
            present = name in existing_views
            report["views"][name] = present
            if not present:
                report["ok"] = False
                report["errors"].append(f"Missing view: {name}")

        try:
            conn.execute("SELECT COUNT(*) FROM users").fetchone()
            conn.execute("SELECT COUNT(*) FROM payments").fetchone()
            conn.execute("SELECT COUNT(*) FROM generated_files").fetchone()
            report["queries_ok"] = True
        except sqlite3.Error as exc:
            report["queries_ok"] = False
            report["ok"] = False
            report["errors"].append(f"Query check failed: {exc}")

    return report
