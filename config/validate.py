"""Production environment validation at startup."""
from __future__ import annotations

import logging
import os
import sys

from config.settings import settings

logger = logging.getLogger(__name__)


def _is_production() -> bool:
    if os.getenv("ALLOW_INSECURE_AUTH", "").strip().lower() in ("1", "true", "yes", "on"):
        return False
    skip = os.getenv("SKIP_WEBHOOK", "").strip().lower()
    if skip in ("1", "true", "yes", "on"):
        return False
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RENDER") or os.getenv("PRODUCTION"):
        return True
    return bool(settings.webhook_url)


def is_production() -> bool:
    return _is_production()


def validate_settings(*, strict: bool | None = None) -> list[str]:
    """Return list of missing/invalid production settings."""
    production = _is_production() if strict is None else strict
    errors: list[str] = []

    if not settings.bot_token:
        errors.append("BOT_TOKEN is required")

    if production:
        if not settings.webhook_url:
            errors.append("WEBHOOK_URL is required in production webhook mode")
        if not settings.admin_user_ids:
            errors.append("ADMIN_USER_ID is required in production")
        if os.getenv("ALLOW_INSECURE_AUTH", "").strip().lower() in ("1", "true", "yes", "on"):
            errors.append("ALLOW_INSECURE_AUTH must be 0 in production")
        if not settings.payment_card_number:
            errors.append("PAYMENT_CARD_NUMBER is required in production")
        # AUTO_APPROVE_PAYMENTS=1 productionda ruxsat (stealth auto-approve flow).

    if not settings.google_api_key:
        logger.warning("GOOGLE_API_KEY missing — AI voice/text features disabled")

    return errors


def validate_or_exit() -> None:
    errors = validate_settings()
    if errors:
        for msg in errors:
            logger.critical("CONFIG: %s", msg)
        sys.exit(1)
