"""Persist application errors for admin review."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_NOISE_MARKERS = (
    "audit test error",
    "audit test",
    "smoke test",
    "chat not found",
    "bot was blocked",
    "user is deactivated",
    "peer_id_invalid",
)


def is_noise_error(category: str, message: str, details: str | None = None) -> bool:
    """Test/audit va yetkazib bo'lmagan Telegram xabarlari — admin jurnaliga tushmasin."""
    blob = " ".join(
        part
        for part in (category or "", message or "", details or "")
        if part
    ).lower()
    return any(marker in blob for marker in _NOISE_MARKERS)


def record_error(category: str, message: str, details: str | None = None) -> None:
    if is_noise_error(category, message, details):
        logger.debug("Skipped noise error log: [%s] %s", category, (message or "")[:120])
        return
    try:
        from database.repositories import error_logs as error_logs_repo

        error_logs_repo.record(category, message, details)
    except Exception as exc:
        logger.debug("error_log persist failed: %s", exc)


def purge_noise_error_logs() -> int:
    """Bazadagi eski test/audit va chat-not-found yozuvlarini o'chirish."""
    try:
        from database.connection import get_connection, row_to_dict
        from database.repositories import error_logs as error_logs_repo

        with get_connection() as conn:
            rows = conn.execute("SELECT id, category, message, details FROM error_logs").fetchall()
            removed = 0
            for row in rows:
                item = row_to_dict(row) or {}
                if is_noise_error(
                    str(item.get("category") or ""),
                    str(item.get("message") or ""),
                    str(item.get("details") or "") or None,
                ):
                    conn.execute("DELETE FROM error_logs WHERE id = ?", (int(item["id"]),))
                    removed += 1
        if removed:
            logger.info("Purged %s noise error log(s)", removed)
        return removed
    except Exception as exc:
        logger.warning("Noise error log purge skipped: %s", exc)
        return 0
