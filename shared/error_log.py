"""Persist application errors for admin review."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def record_error(category: str, message: str, details: str | None = None) -> None:
    try:
        from database.repositories import error_logs as error_logs_repo

        error_logs_repo.record(category, message, details)
    except Exception as exc:
        logger.debug("error_log persist failed: %s", exc)
