"""Periodic housekeeping for append-only log tables."""
from __future__ import annotations

import sqlite3

from database.connection import get_connection

# Tables that get a row per request/event and are only ever read for recent periods.
_LOG_TABLES = ("ai_request_logs", "security_events", "error_logs")


def prune_log_tables(*, keep_days: int = 30) -> int:
    """Delete log rows older than keep_days. Returns number of rows removed."""
    keep_days = max(1, min(int(keep_days), 365))
    deleted = 0
    with get_connection() as conn:
        for table in _LOG_TABLES:
            try:
                cur = conn.execute(
                    f"DELETE FROM {table} WHERE created_at < datetime('now', ?)",
                    (f"-{keep_days} days",),
                )
                deleted += int(cur.rowcount or 0)
            except sqlite3.OperationalError:
                continue  # table not present on this install
    return deleted
