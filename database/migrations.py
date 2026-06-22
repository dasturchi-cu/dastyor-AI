"""Versioned SQLite migrations — additive, data-safe."""
from __future__ import annotations

import logging
import sqlite3
from typing import Callable

logger = logging.getLogger(__name__)

MigrationFn = Callable[[sqlite3.Connection], None]


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name = ?",
        (name,),
    ).fetchone()
    return row is not None


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _add_column(conn: sqlite3.Connection, table: str, ddl: str) -> None:
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def _ensure_schema_migrations(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            version     INTEGER NOT NULL UNIQUE,
            name        TEXT NOT NULL,
            applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def _applied_versions(conn: sqlite3.Connection) -> set[int]:
    if not _table_exists(conn, "schema_migrations"):
        return set()
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {int(r[0]) for r in rows}


def _mark_applied(conn: sqlite3.Connection, version: int, name: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (?, ?)",
        (version, name),
    )


def migration_001_legacy_columns(conn: sqlite3.Connection) -> None:
    """Add new columns to existing installs without dropping data."""
    if _table_exists(conn, "users"):
        cols = _columns(conn, "users")
        if "full_name" not in cols:
            _add_column(conn, "users", "full_name TEXT")
        if "first_seen_at" not in cols:
            _add_column(conn, "users", "first_seen_at TEXT")
            conn.execute(
                "UPDATE users SET first_seen_at = COALESCE(created_at, datetime('now')) "
                "WHERE first_seen_at IS NULL"
            )
        if "last_seen_at" not in cols:
            _add_column(conn, "users", "last_seen_at TEXT")
        if "total_cv" not in cols:
            _add_column(conn, "users", "total_cv INTEGER NOT NULL DEFAULT 0")
        if "total_obyektivka" not in cols:
            _add_column(conn, "users", "total_obyektivka INTEGER NOT NULL DEFAULT 0")
        if "total_purchases" not in cols:
            _add_column(conn, "users", "total_purchases INTEGER NOT NULL DEFAULT 0")
        if "first_name" not in cols:
            _add_column(conn, "users", "first_name TEXT")
        if "last_name" not in cols:
            _add_column(conn, "users", "last_name TEXT")
        if "last_active_at" not in cols:
            _add_column(conn, "users", "last_active_at TEXT")
        if "credits" not in cols:
            _add_column(conn, "users", "credits INTEGER NOT NULL DEFAULT 0")
        if "is_blocked" not in cols:
            _add_column(conn, "users", "is_blocked INTEGER NOT NULL DEFAULT 0")

    if _table_exists(conn, "payments"):
        cols = _columns(conn, "payments")
        if "payment_number" not in cols:
            _add_column(conn, "payments", "payment_number TEXT")
        if "amount" not in cols:
            _add_column(conn, "payments", "amount INTEGER NOT NULL DEFAULT 0")
        if "screenshot_path" not in cols:
            _add_column(conn, "payments", "screenshot_path TEXT")
        if "receipt_path" not in cols:
            _add_column(conn, "payments", "receipt_path TEXT")
        if "document_type" not in cols:
            _add_column(conn, "payments", "document_type TEXT")
        if "approved_by" not in cols:
            _add_column(conn, "payments", "approved_by INTEGER")
        if "approved_at" not in cols:
            _add_column(conn, "payments", "approved_at TEXT")
        if "pending_reminder_sent_at" not in cols:
            _add_column(conn, "payments", "pending_reminder_sent_at TEXT")
        if "admin_note" not in cols:
            _add_column(conn, "payments", "admin_note TEXT")
        if "updated_at" not in cols:
            _add_column(conn, "payments", "updated_at TEXT")
        conn.execute(
            """
            UPDATE payments
            SET screenshot_path = receipt_path
            WHERE screenshot_path IS NULL AND receipt_path IS NOT NULL
            """
        )
        conn.execute(
            """
            UPDATE payments
            SET receipt_path = screenshot_path
            WHERE receipt_path IS NULL AND screenshot_path IS NOT NULL
            """
        )


def migration_002_new_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            document_type TEXT NOT NULL CHECK (document_type IN ('cv', 'obyektivka')),
            file_path TEXT,
            is_unlocked INTEGER NOT NULL DEFAULT 0,
            payment_id INTEGER REFERENCES payments(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id);
        CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
        CREATE INDEX IF NOT EXISTS idx_documents_created ON documents(created_at DESC);

        CREATE TABLE IF NOT EXISTS cv_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            template_name TEXT,
            pdf_path TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_cv_documents_user ON cv_documents(user_id);
        CREATE INDEX IF NOT EXISTS idx_cv_documents_created ON cv_documents(created_at DESC);

        CREATE TABLE IF NOT EXISTS obyektivka_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            docx_path TEXT NOT NULL,
            pdf_preview_path TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_oby_documents_user ON obyektivka_documents(user_id);
        CREATE INDEX IF NOT EXISTS idx_oby_documents_created ON obyektivka_documents(created_at DESC);

        CREATE TABLE IF NOT EXISTS support_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            message TEXT NOT NULL,
            admin_reply TEXT,
            status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'replied', 'closed')),
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_support_user ON support_messages(user_id);
        CREATE INDEX IF NOT EXISTS idx_support_status ON support_messages(status);
        CREATE INDEX IF NOT EXISTS idx_support_created ON support_messages(created_at DESC);

        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_admin_logs_admin ON admin_logs(admin_id);
        CREATE INDEX IF NOT EXISTS idx_admin_logs_created ON admin_logs(created_at DESC);
        """
    )


def migration_003_migrate_generated_files(conn: sqlite3.Connection) -> None:
    """Move legacy generated_files table rows into cv/oby document tables."""
    if not _table_exists(conn, "generated_files"):
        return
    # Real table (not view) has sqlite internal type 'table'
    row = conn.execute(
        "SELECT type FROM sqlite_master WHERE name = 'generated_files'"
    ).fetchone()
    if not row or str(row[0]).lower() != "table":
        return

    rows = conn.execute(
        "SELECT user_id, file_type, file_path, file_name, created_at FROM generated_files"
    ).fetchall()
    for r in rows:
        ft = str(r["file_type"] or "").lower()
        if ft == "cv":
            conn.execute(
                """
                INSERT INTO cv_documents (user_id, template_name, pdf_path, created_at)
                VALUES (?, ?, ?, COALESCE(?, datetime('now')))
                """,
                (r["user_id"], r["file_name"], r["file_path"], r["created_at"]),
            )
        elif ft == "obyektivka":
            conn.execute(
                """
                INSERT INTO obyektivka_documents (user_id, docx_path, created_at)
                VALUES (?, ?, COALESCE(?, datetime('now')))
                """,
                (r["user_id"], r["file_path"], r["created_at"]),
            )

    conn.execute("DROP TABLE generated_files")
    logger.info("Migrated %d generated_files rows to cv/obyektivka_documents", len(rows))


def migration_004_generated_files_view(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "generated_files"):
        return
    conn.executescript(
        """
        CREATE VIEW generated_files AS
        SELECT id, user_id, 'cv' AS file_type, pdf_path AS file_path,
               template_name AS file_name, created_at
        FROM cv_documents
        UNION ALL
        SELECT id, user_id, 'obyektivka' AS file_type, docx_path AS file_path,
               NULL AS file_name, created_at
        FROM obyektivka_documents;
        """
    )


def migration_005_sync_user_counters(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "users"):
        return
    conn.execute(
        """
        UPDATE users SET total_cv = (
            SELECT COUNT(*) FROM cv_documents c WHERE c.user_id = users.id
        )
        """
    )
    conn.execute(
        """
        UPDATE users SET total_obyektivka = (
            SELECT COUNT(*) FROM obyektivka_documents o WHERE o.user_id = users.id
        )
        """
    )
    conn.execute(
        """
        UPDATE users SET total_purchases = (
            SELECT COUNT(*) FROM payments p
            WHERE p.user_id = users.id AND p.status = 'APPROVED'
        )
        """
    )
    conn.execute(
        """
        UPDATE users SET full_name = TRIM(
            COALESCE(first_name, '') || ' ' || COALESCE(last_name, '')
        )
        WHERE (full_name IS NULL OR full_name = '')
          AND (first_name IS NOT NULL OR last_name IS NOT NULL)
        """
    )
    conn.execute(
        """
        UPDATE users SET last_seen_at = COALESCE(last_active_at, updated_at)
        WHERE last_seen_at IS NULL
        """
    )


def migration_006_payment_numbers(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "payments"):
        return
    rows = conn.execute(
        "SELECT id, created_at FROM payments WHERE payment_number IS NULL OR payment_number = ''"
    ).fetchall()
    for r in rows:
        pid = int(r["id"])
        num = f"PAY-{pid:06d}"
        conn.execute(
            "UPDATE payments SET payment_number = ? WHERE id = ?",
            (num, pid),
        )


def migration_007_settings_id_column(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "settings"):
        return
    cols = _columns(conn, "settings")
    if "id" in cols:
        return
    conn.executescript(
        """
        CREATE TABLE settings_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL UNIQUE,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        INSERT INTO settings_new (key, value, updated_at)
        SELECT key, value, COALESCE(updated_at, datetime('now')) FROM settings;
        DROP TABLE settings;
        ALTER TABLE settings_new RENAME TO settings;
        """
    )


def migration_008_extra_indexes(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_id);
        CREATE INDEX IF NOT EXISTS idx_payments_number ON payments(payment_number);
        CREATE INDEX IF NOT EXISTS idx_payments_created ON payments(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active_at);
        CREATE INDEX IF NOT EXISTS idx_users_last_seen ON users(last_seen_at);
        CREATE INDEX IF NOT EXISTS idx_users_created ON users(created_at DESC);
        """
    )


MIGRATIONS: list[tuple[int, str, MigrationFn]] = [
    (1, "legacy_columns", migration_001_legacy_columns),
    (2, "new_tables", migration_002_new_tables),
    (3, "migrate_generated_files", migration_003_migrate_generated_files),
    (4, "generated_files_view", migration_004_generated_files_view),
    (5, "sync_user_counters", migration_005_sync_user_counters),
    (6, "payment_numbers", migration_006_payment_numbers),
    (7, "settings_id_column", migration_007_settings_id_column),
    (8, "extra_indexes", migration_008_extra_indexes),
]


def run_migrations(conn: sqlite3.Connection) -> None:
    _ensure_schema_migrations(conn)
    applied = _applied_versions(conn)
    for version, name, fn in MIGRATIONS:
        if version in applied:
            continue
        logger.info("Applying migration %03d_%s", version, name)
        fn(conn)
        _mark_applied(conn, version, name)
