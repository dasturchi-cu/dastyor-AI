"""Aggregated security metrics for admin dashboard."""
from __future__ import annotations

from typing import Any

from config.settings import settings
from database.connection import get_connection
from database.repositories import security_events as sec_repo
from database.repositories import users as users_repo


def _count_blocked_users() -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM users WHERE is_blocked = 1"
        ).fetchone()
    return int(row[0]) if row else 0


def _active_sessions_estimate() -> int:
    """Users active within online window (proxy for session count)."""
    minutes = max(1, settings.online_user_minutes)
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) FROM users
            WHERE datetime(COALESCE(last_active_at, last_seen_at)) >= datetime('now', ?)
            """,
            (f"-{minutes} minutes",),
        ).fetchone()
    return int(row[0]) if row else 0


def _active_users_today() -> int:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) FROM users
            WHERE date(COALESCE(last_active_at, last_seen_at)) = date('now')
            """
        ).fetchone()
    return int(row[0]) if row else 0


def _ai_abuse_today() -> int:
    with get_connection() as conn:
        if not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ai_request_logs'"
        ).fetchone():
            return 0
        row = conn.execute(
            """
            SELECT COUNT(*) FROM ai_request_logs
            WHERE date(request_time) = date('now')
              AND status IN ('rate_limit', 'quota')
            """
        ).fetchone()
    return int(row[0]) if row else 0


def compute_security_score(snapshot: dict[str, Any]) -> int:
    """0–100 posture score (higher is better)."""
    score = 100
    if settings.allow_insecure_auth:
        score -= 40
    if settings.auto_approve_payments:
        score -= 10
    if not settings.turnstile_secret_key:
        score -= 5
    if not settings.webhook_secret:
        score -= 10
    failed = int(snapshot.get("failed_logins_24h") or 0)
    rate_hits = int(snapshot.get("rate_limit_hits_24h") or 0)
    fraud = int(snapshot.get("fraud_attempts_24h") or 0)
    score -= min(20, failed // 5)
    score -= min(15, rate_hits // 20)
    score -= min(25, fraud * 5)
    return max(0, min(100, score))


def security_snapshot() -> dict[str, Any]:
    failed_logins = sec_repo.count_since("auth_failed", 24)
    rate_limit_hits = sec_repo.count_since("rate_limit", 24)
    fraud_attempts = sec_repo.count_since("fraud_payment", 24)
    ai_abuse = sec_repo.count_since("ai_abuse", 24) + _ai_abuse_today()
    file_rejected = sec_repo.count_since("file_rejected", 24)
    suspicious_ips = sec_repo.top_ips(24, 10)

    snap: dict[str, Any] = {
        "active_users": _active_users_today(),
        "active_sessions": _active_sessions_estimate(),
        "failed_logins_24h": failed_logins,
        "rate_limit_hits_24h": rate_limit_hits,
        "fraud_attempts_24h": fraud_attempts,
        "payment_fraud_24h": fraud_attempts,
        "ai_abuse_24h": ai_abuse,
        "blocked_users": _count_blocked_users(),
        "suspicious_ips": suspicious_ips,
        "file_rejections_24h": file_rejected,
        "users_total": users_repo.count_users(),
        "recent_events": sec_repo.list_recent(8),
    }
    snap["security_score"] = compute_security_score(snap)
    return snap
