"""AI quota state persistence and history."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from database.connection import get_connection, row_to_dict


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_all_states() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM ai_quota_state ORDER BY provider, key_index").fetchall()
    return [row_to_dict(r) for r in rows if row_to_dict(r)]


def upsert_state(
    *,
    provider: str,
    key_index: int,
    model: str | None,
    quota_percent: float,
    requests_used: int,
    requests_remaining: int,
    status: str,
    last_success: str | None,
    last_failure: str | None,
    reset_time: str | None,
    health_status: str,
    daily_limit: int,
) -> None:
    now = _utc_iso()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO ai_quota_state (
                provider, key_index, model, quota_percent, requests_used,
                requests_remaining, status, last_success, last_failure,
                reset_time, health_status, daily_limit, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(provider, key_index) DO UPDATE SET
                model = excluded.model,
                quota_percent = excluded.quota_percent,
                requests_used = excluded.requests_used,
                requests_remaining = excluded.requests_remaining,
                status = excluded.status,
                last_success = excluded.last_success,
                last_failure = excluded.last_failure,
                reset_time = excluded.reset_time,
                health_status = excluded.health_status,
                daily_limit = excluded.daily_limit,
                updated_at = excluded.updated_at
            """,
            (
                provider,
                key_index,
                model,
                quota_percent,
                requests_used,
                requests_remaining,
                status,
                last_success,
                last_failure,
                reset_time,
                health_status,
                daily_limit,
                now,
            ),
        )


def insert_history(
    *,
    provider: str,
    key_index: int,
    quota_percent: float,
    requests_used: int,
    requests_remaining: int,
    status: str,
    event_type: str = "snapshot",
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO ai_quota_history (
                provider, key_index, quota_percent, requests_used,
                requests_remaining, status, event_type, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                provider,
                key_index,
                quota_percent,
                requests_used,
                requests_remaining,
                status,
                event_type,
                _utc_iso(),
            ),
        )


def list_history(
    *,
    provider: str | None = None,
    key_index: int | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 200))
    sql = "SELECT * FROM ai_quota_history WHERE 1=1"
    params: list[Any] = []
    if provider:
        sql += " AND provider = ?"
        params.append(provider)
    if key_index is not None:
        sql += " AND key_index = ?"
        params.append(key_index)
    sql += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [row_to_dict(r) for r in rows if row_to_dict(r)]


def list_recent_reset_events(limit: int = 20) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 100))
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM ai_quota_history
            WHERE event_type = 'quota_reset'
            ORDER BY updated_at DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [row_to_dict(r) for r in rows if row_to_dict(r)]
