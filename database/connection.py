"""SQLite connection pool (per-thread) and initialization."""
from __future__ import annotations

import logging
import shutil
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from config.settings import DATA_DIR, PROJECT_ROOT, settings
from database.migrations import run_migrations
from database.verify import check_db_integrity, verify_schema

logger = logging.getLogger(__name__)

_schema_lock = threading.Lock()
_initialized = False
_cleaning_test_data = False
_local = threading.local()


def _schema_path() -> Path:
    return PROJECT_ROOT / "database" / "schema.sql"


def _configure_connection(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA cache_size = -8000")
    conn.execute("PRAGMA mmap_size = 268435456")


def _legacy_db_candidates() -> list[Path]:
    """Older DB locations — imported into settings.db_path when target is missing."""
    return [
        DATA_DIR / "app.db",
        DATA_DIR / "hujjatchi.db",
        PROJECT_ROOT / "database" / "app.db",
        PROJECT_ROOT / "data" / "app.db",
        PROJECT_ROOT / "data" / "hujjatchi.db",
        PROJECT_ROOT / "database" / "hujjatchi.db",
    ]


def _db_user_count(path: Path) -> int:
    """Return user row count, or -1 if file missing/unreadable."""
    if not path.is_file() or path.stat().st_size == 0:
        return -1
    try:
        with sqlite3.connect(path) as conn:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'"
            ).fetchone()
            if not row:
                return 0
            return int(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] or 0)
    except sqlite3.Error:
        return -1


def _import_legacy_database(target: Path) -> None:
    """Copy the richest legacy DB into target when target file does not exist."""
    if target.is_file():
        return

    best_legacy: Path | None = None
    best_count = 0
    for legacy in _legacy_db_candidates():
        if not legacy.is_file():
            continue
        try:
            if legacy.resolve() == target.resolve():
                continue
        except OSError:
            if legacy == target:
                continue
        count = _db_user_count(legacy)
        if count > best_count:
            best_count = count
            best_legacy = legacy

    if best_legacy is None or best_count <= 0:
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best_legacy, target)
    logger.info(
        "Imported legacy database %s -> %s (%d users)",
        best_legacy.resolve(),
        target.resolve(),
        best_count,
    )


def _pooled_connection() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        init_db()
        db_path = settings.db_path.resolve()
        logger.info("SQLite connect: %s", db_path)
        conn = sqlite3.connect(db_path, check_same_thread=False)
        _configure_connection(conn)
        _local.conn = conn
    return conn


def initialize_database() -> dict[str, Any]:
    """
    Create database/app.db if missing, create tables, run migrations, verify.
    Called automatically on bot / FastAPI startup.
    """
    global _initialized, _cleaning_test_data
    with _schema_lock:
        db_path = settings.db_path.resolve()
        logger.info("SQLite initialize: %s", db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        had_db = db_path.is_file()
        _import_legacy_database(db_path)
        imported_legacy = not had_db and db_path.is_file()

        if not _initialized:
            with sqlite3.connect(db_path) as conn:
                _configure_connection(conn)
                if not had_db and not imported_legacy:
                    schema = _schema_path().read_text(encoding="utf-8")
                    conn.executescript(schema)
                    logger.info("Created new SQLite database: %s", db_path)
                run_migrations(conn)
                conn.commit()
            _initialized = True
        else:
            with sqlite3.connect(db_path) as conn:
                _configure_connection(conn)
                run_migrations(conn)
                conn.commit()

        ok, msg = check_db_integrity()
        if not ok:
            raise RuntimeError(f"SQLite integrity check failed: {msg}")

        report = verify_schema()
        if not report["ok"]:
            logger.warning("Database schema verification issues: %s", report["errors"])
        else:
            logger.info(
                "SQLite ready: %s (%d tables, integrity=%s)",
                db_path,
                len(report["tables"]),
                msg,
            )

    if _should_purge_test_data_on_startup():
        if _cleaning_test_data:
            return report

        _cleaning_test_data = True
        try:
            from shared.test_data_cleanup import purge_all_test_data

            purge_all_test_data()
        except Exception as exc:
            logger.warning("Test data purge skipped: %s", exc)
        finally:
            _cleaning_test_data = False

    return report


def _should_purge_test_data_on_startup() -> bool:
    import os

    if os.getenv("_HUJJATCHI_TEST", "").strip() == "1":
        return True
    return os.getenv("PURGE_TEST_DATA_ON_STARTUP", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def init_db() -> None:
    """Backward-compatible alias for initialize_database()."""
    initialize_database()


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Per-thread pooled connection; commit on success."""
    conn = _pooled_connection()
    try:
        yield conn
        conn.commit()
        # Ensure WAL pages are visible to other connections / after restart.
        try:
            conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
        except sqlite3.Error:
            pass
    except Exception:
        conn.rollback()
        raise


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}
