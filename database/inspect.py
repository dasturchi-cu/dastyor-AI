"""SQLite inspection — admin debug + external tools (DB Browser, SQLiteStudio)."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from config.settings import PROJECT_ROOT, settings
from database.verify import REQUIRED_INDEXES, REQUIRED_TABLES, REQUIRED_VIEWS, check_db_integrity


def _format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.2f} MB"


def _file_sizes(db_path: Path) -> dict[str, Any]:
    main = db_path.stat().st_size if db_path.is_file() else 0
    wal = db_path.with_suffix(db_path.suffix + "-wal")
    shm = db_path.with_suffix(db_path.suffix + "-shm")
    wal_size = wal.stat().st_size if wal.is_file() else 0
    shm_size = shm.stat().st_size if shm.is_file() else 0
    total = main + wal_size + shm_size
    return {
        "main_bytes": main,
        "wal_bytes": wal_size,
        "shm_bytes": shm_size,
        "total_bytes": total,
        "main_human": _format_bytes(main),
        "total_human": _format_bytes(total),
        "wal_file": str(wal) if wal.is_file() else None,
        "shm_file": str(shm) if shm.is_file() else None,
    }


def get_database_info() -> dict[str, Any]:
    """Full SQLite inspection payload for /admin/db-info."""
    db_path = settings.db_path.resolve()
    exists = db_path.is_file()

    info: dict[str, Any] = {
        "ok": exists,
        "db_path": str(db_path),
        "db_path_relative": str(db_path.relative_to(PROJECT_ROOT))
        if db_path.is_relative_to(PROJECT_ROOT)
        else str(db_path),
        "file_exists": exists,
        "external_tools": {
            "db_browser": "Open db_path in DB Browser for SQLite or SQLiteStudio",
            "note": "WAL mode: also copy -wal and -shm sidecar files if copying live DB",
        },
        "tables": [],
        "views": [],
        "indexes": [],
        "row_counts": {},
        "schema_migrations": [],
        "pragmas": {},
        "integrity": "unknown",
        "size": {},
        "totals": {"tables": 0, "rows": 0, "indexes": 0},
    }

    if not exists:
        info["ok"] = False
        info["error"] = "Database file not found — run initialize_database() on startup"
        return info

    info["size"] = _file_sizes(db_path)
    ok, msg = check_db_integrity()
    info["integrity"] = msg
    info["ok"] = ok

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        for key, pragma in (
            ("journal_mode", "journal_mode"),
            ("foreign_keys", "foreign_keys"),
            ("user_version", "user_version"),
        ):
            row = conn.execute(f"PRAGMA {pragma}").fetchone()
            info["pragmas"][key] = row[0] if row else None

        if _table_exists(conn, "schema_migrations"):
            rows = conn.execute(
                "SELECT version, name, applied_at FROM schema_migrations ORDER BY version"
            ).fetchall()
            info["schema_migrations"] = [dict(r) for r in rows]

        user_tables = conn.execute(
            """
            SELECT name, sql FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
        for row in user_tables:
            name = row["name"]
            count = _safe_count(conn, name)
            info["tables"].append({"name": name, "rows": count})
            info["row_counts"][name] = count

        view_rows = conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'view' ORDER BY name
            """
        ).fetchall()
        for row in view_rows:
            name = row["name"]
            count = _safe_count(conn, name)
            info["views"].append({"name": name, "rows": count})
            info["row_counts"][name] = count

        index_rows = conn.execute(
            """
            SELECT name, tbl_name, sql FROM sqlite_master
            WHERE type = 'index' AND name NOT LIKE 'sqlite_%'
            ORDER BY tbl_name, name
            """
        ).fetchall()
        for row in index_rows:
            info["indexes"].append(
                {
                    "name": row["name"],
                    "table": row["tbl_name"],
                    "sql": row["sql"],
                }
            )

    info["totals"]["tables"] = len(info["tables"])
    info["totals"]["rows"] = sum(t["rows"] for t in info["tables"])
    info["totals"]["indexes"] = len(info["indexes"])
    info["required"] = {
        "tables": {t: t in info["row_counts"] for t in REQUIRED_TABLES},
        "indexes": {i: any(x["name"] == i for x in info["indexes"]) for i in REQUIRED_INDEXES},
        "views": {v: any(x["name"] == v for x in info["views"]) for v in REQUIRED_VIEWS},
    }
    return info


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def _safe_count(conn: sqlite3.Connection, table: str) -> int:
    try:
        row = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()
        return int(row[0]) if row else 0
    except sqlite3.Error:
        return -1
