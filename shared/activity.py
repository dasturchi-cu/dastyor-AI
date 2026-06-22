"""Fire-and-forget activity logging for admin live feed."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def log_register(telegram_id: int, name: str) -> None:
    _safe_record("register", actor_name=name, telegram_id=telegram_id)


def log_cv(telegram_id: int, name: str) -> None:
    _safe_record("cv", actor_name=name, telegram_id=telegram_id)


def log_obyektivka(telegram_id: int, name: str) -> None:
    _safe_record("obyektivka", actor_name=name, telegram_id=telegram_id)


def log_payment(telegram_id: int, name: str, *, document: str = "") -> None:
    _safe_record("payment", actor_name=name, telegram_id=telegram_id, detail=document)


def log_download(telegram_id: int, name: str, *, document: str = "") -> None:
    _safe_record("download", actor_name=name, telegram_id=telegram_id, detail=document)


def _safe_record(
    event_type: str,
    *,
    actor_name: str = "",
    telegram_id: int | None = None,
    detail: str = "",
) -> None:
    try:
        from database.repositories import activity as activity_repo

        activity_repo.record(
            event_type,
            actor_name=actor_name,
            telegram_id=telegram_id,
            detail=detail,
        )
    except Exception as exc:
        logger.debug("activity log failed: %s", exc)
