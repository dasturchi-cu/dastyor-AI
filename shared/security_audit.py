"""Security event audit logging."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

SEVERITY_INFO = "info"
SEVERITY_WARN = "warn"
SEVERITY_CRITICAL = "critical"

EVENT_AUTH_FAILED = "auth_failed"
EVENT_AUTH_SUCCESS = "auth_success"
EVENT_RATE_LIMIT = "rate_limit"
EVENT_FRAUD_PAYMENT = "fraud_payment"
EVENT_AI_ABUSE = "ai_abuse"
EVENT_FILE_REJECTED = "file_rejected"
EVENT_ADMIN_ACCESS = "admin_access"
EVENT_SUSPICIOUS_IP = "suspicious_ip"
EVENT_WEBHOOK_REJECTED = "webhook_rejected"
EVENT_NOTIFY_ABUSE = "notify_abuse"
EVENT_ORIGIN_REJECTED = "origin_rejected"


def log_security_event(
    event_type: str,
    *,
    severity: str = SEVERITY_INFO,
    ip: str | None = None,
    user_id: int | None = None,
    details: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Persist security event and emit structured log line."""
    detail_str = (details or "")[:2000]
    if extra:
        try:
            import json

            detail_str = (detail_str + " " + json.dumps(extra, ensure_ascii=False))[:2000]
        except Exception:
            pass

    try:
        from database.repositories import security_events as sec_repo

        sec_repo.record(
            event_type=event_type,
            severity=severity,
            ip=ip,
            user_id=user_id,
            details=detail_str or None,
        )
    except Exception as exc:
        logger.warning("security event persist failed: %s", exc)

    logger.info(
        "SECURITY event=%s severity=%s ip=%s user=%s detail=%s",
        event_type,
        severity,
        ip or "-",
        user_id or "-",
        (detail_str or "")[:200],
    )
