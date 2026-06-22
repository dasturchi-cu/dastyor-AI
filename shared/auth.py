"""Resolve Telegram user from validated session token."""
from __future__ import annotations

import os
from typing import Optional

from shared.session_service import resolve_telegram_id

_INSECURE = os.getenv("ALLOW_INSECURE_AUTH", "").strip().lower() in ("1", "true", "yes", "on")


def insecure_auth_allowed() -> bool:
    """Dev/smoke only — never enable in production."""
    return _INSECURE


def resolve_uid(telegram_id: Optional[str] = None, token: Optional[str] = None) -> Optional[int]:
    """
    Production: session token only (issued after initData-validated /api/auth).
    Dev: optional telegram_id when ALLOW_INSECURE_AUTH=1.
    """
    if token:
        uid = resolve_telegram_id(token)
        if uid and str(uid).isdigit():
            return int(uid)
    if _INSECURE and telegram_id and str(telegram_id).strip().isdigit():
        return int(telegram_id)
    return None


def is_admin(telegram_id: int | None) -> bool:
    if not telegram_id:
        return False
    from config.settings import settings

    return int(telegram_id) in settings.admin_user_ids
