"""App settings repository."""
from __future__ import annotations

import time

from database.connection import get_connection

_MAINT_CACHE: dict[str, float | bool] = {"v": False, "ts": 0.0}
_MAINT_TTL = 5.0


def get(key: str, default: str = "") -> str:
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row else default


def set_value(key: str, value: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')
            """,
            (key, value),
        )
    if key == "maintenance_mode":
        _MAINT_CACHE["ts"] = 0.0


def is_maintenance() -> bool:
    now = time.monotonic()
    if now - float(_MAINT_CACHE["ts"]) < _MAINT_TTL:
        return bool(_MAINT_CACHE["v"])
    v = get("maintenance_mode", "0").strip().lower() in ("1", "true", "yes")
    _MAINT_CACHE["v"] = v
    _MAINT_CACHE["ts"] = now
    return v
