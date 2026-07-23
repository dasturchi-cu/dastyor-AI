"""Database integrity and schema verification."""
from __future__ import annotations

import sqlite3
import time
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
    "ai_request_logs",
    "ai_quota_state",
    "ai_quota_history",
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

# Full PRAGMA integrity_check on a large DB is multi-second and must NOT run
# on every Docker/K8s /health probe (blocks the asyncio event loop).
_INTEGRITY_CACHE_TTL_SEC = 3600.0
_integrity_cache: tuple[float, bool, str] | None = None


def check_db_integrity(*, force: bool = False) -> tuple[bool, str]:
    global _integrity_cache
    now = time.monotonic()
    if not force and _integrity_cache is not None:
        cached_at, ok, msg = _integrity_cache
        if now - cached_at < _INTEGRITY_CACHE_TTL_SEC:
            return ok, msg

    with sqlite3.connect(settings.db_path) as conn:
        row = conn.execute("PRAGMA integrity_check").fetchone()
    msg = str(row[0]) if row else "unknown"
    ok = msg == "ok"
    _integrity_cache = (now, ok, msg)
    return ok, msg


def quick_health_check() -> dict[str, Any]:
    """Fast liveness/readiness for /health — no full integrity scan."""
    report: dict[str, Any] = {
        "ok": True,
        "db_path": str(settings.db_path),
        "errors": [],
        "tables_ok": False,
    }
    if not settings.db_path.is_file():
        report["ok"] = False
        report["errors"].append(f"Database file missing: {settings.db_path}")
        return report

    try:
        with sqlite3.connect(f"file:{settings.db_path}?mode=ro", uri=True, timeout=2.0) as conn:
            existing = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            missing = [t for t in ("users", "payments", "error_logs") if t not in existing]
            if missing:
                report["ok"] = False
                report["errors"].append(f"Missing core tables: {', '.join(missing)}")
            else:
                report["tables_ok"] = True
                conn.execute("SELECT 1 FROM users LIMIT 1").fetchone()
    except sqlite3.Error as exc:
        report["ok"] = False
        report["errors"].append(f"DB probe failed: {exc}")
    return report


def verify_schema(*, include_integrity: bool = True) -> dict[str, Any]:
    """Return verification report for startup / deep admin checks."""
    report: dict[str, Any] = {
        "ok": True,
        "db_path": str(settings.db_path),
        "tables": {},
        "indexes": {},
        "views": {},
        "integrity": "skipped",
        "errors": [],
    }

    if not settings.db_path.is_file():
        report["ok"] = False
        report["errors"].append(f"Database file missing: {settings.db_path}")
        return report

    if include_integrity:
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
