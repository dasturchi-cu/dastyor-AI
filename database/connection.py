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


def _import_legacy_database(target: Path) -> None:
    """Copy old hujjatchi.db into database/app.db if new file does not exist."""
    if target.is_file():
        return
    for legacy in _legacy_db_candidates():
        if legacy.is_file() and legacy.resolve() != target.resolve():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(legacy, target)
            logger.info("Imported legacy database %s -> %s", legacy, target)
            return


def _pooled_connection() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        init_db()
        conn = sqlite3.connect(settings.db_path, check_same_thread=False)
        _configure_connection(conn)
        _local.conn = conn
    return conn


def initialize_database() -> dict[str, Any]:
    """
    Create database/app.db if missing, create tables, run migrations, verify.
    Called automatically on bot / FastAPI startup.
    """
    global _initialized
    with _schema_lock:
        db_path = settings.db_path
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
                db_path.resolve(),
                len(report["tables"]),
                msg,
            )

        canonical = (DATA_DIR / "app.db").resolve()
        resolved = db_path.resolve()
        if resolved != canonical:
            logger.warning(
                "DB_PATH (%s) is outside DATA_DIR (%s). "
                "Mount a volume at DATA_DIR and use DB_PATH=%s for deploy persistence.",
                resolved,
                DATA_DIR.resolve(),
                canonical,
            )

    try:
        from database.repositories.users import purge_test_users

        removed = purge_test_users()
        if removed:
            logger.info(
                "Removed %s test/audit user(s) from database: %s",
                len(removed),
                ", ".join(str(t) for t in removed[:12]),
            )
    except Exception as exc:
        logger.warning("Test user purge skipped: %s", exc)

    return report


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
