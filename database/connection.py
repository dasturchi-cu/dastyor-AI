"""SQLite connection pool (per-thread) and initialization."""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from config.settings import PROJECT_ROOT, settings

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


def _pooled_connection() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        init_db()
        conn = sqlite3.connect(settings.db_path, check_same_thread=False)
        _configure_connection(conn)
        _local.conn = conn
    return conn


def _apply_migrations(conn: sqlite3.Connection) -> None:
    """Idempotent schema updates for existing databases."""
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_ai_sessions_user_type
            ON ai_sessions(user_id, session_type, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_id);
        CREATE INDEX IF NOT EXISTS idx_payments_user_status ON payments(user_id, status);
        CREATE INDEX IF NOT EXISTS idx_payments_created ON payments(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_generated_files_created ON generated_files(created_at DESC);
        """
    )
    pay_cols = {row[1] for row in conn.execute("PRAGMA table_info(payments)").fetchall()}
    if "document_type" not in pay_cols:
        conn.execute("ALTER TABLE payments ADD COLUMN document_type TEXT")

    user_cols = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "is_blocked" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN is_blocked INTEGER NOT NULL DEFAULT 0")
    if "last_active_at" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN last_active_at TEXT")
    if "has_cv_access" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN has_cv_access INTEGER NOT NULL DEFAULT 0")
    if "has_objective_access" not in user_cols:
        conn.execute(
            "ALTER TABLE users ADD COLUMN has_objective_access INTEGER NOT NULL DEFAULT 0"
        )

    if "pending_reminder_sent_at" not in pay_cols:
        conn.execute("ALTER TABLE payments ADD COLUMN pending_reminder_sent_at TEXT")

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS error_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            category        TEXT NOT NULL,
            message         TEXT NOT NULL,
            details         TEXT,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_error_logs_category
            ON error_logs(category, created_at DESC);
        CREATE TABLE IF NOT EXISTS activity_events (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type      TEXT NOT NULL,
            user_id         INTEGER REFERENCES users(id) ON DELETE SET NULL,
            actor_name      TEXT,
            detail          TEXT,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_activity_created
            ON activity_events(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active_at);
        CREATE INDEX IF NOT EXISTS idx_generated_type_created
            ON generated_files(file_type, created_at DESC);
        """
    )


def check_db_integrity() -> tuple[bool, str]:
    """Run SQLite PRAGMA integrity_check (ok, message)."""
    with sqlite3.connect(settings.db_path) as conn:
        row = conn.execute("PRAGMA integrity_check").fetchone()
    msg = str(row[0]) if row else "unknown"
    return msg == "ok", msg


def init_db() -> None:
    global _initialized
    with _schema_lock:
        db_path = settings.db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        if not _initialized:
            schema = _schema_path().read_text(encoding="utf-8")
            with sqlite3.connect(db_path) as conn:
                _configure_connection(conn)
                conn.executescript(schema)
                conn.commit()
            _initialized = True
        with sqlite3.connect(db_path) as conn:
            _configure_connection(conn)
            _apply_migrations(conn)
            conn.commit()
        ok, msg = check_db_integrity()
        if not ok:
            raise RuntimeError(f"SQLite integrity check failed: {msg}")


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Per-thread pooled connection; commit on success."""
    conn = _pooled_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}
