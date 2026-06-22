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
        """
    )


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
