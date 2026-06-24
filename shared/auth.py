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
    uid: int | None = None
    if token:
        resolved = resolve_telegram_id(token)
        if resolved and str(resolved).isdigit():
            uid = int(resolved)
    if uid is None and _INSECURE and telegram_id and str(telegram_id).strip().isdigit():
        uid = int(telegram_id)
    if uid is None:
        return None
    if not is_admin(uid):
        from database.repositories import users as users_repo

        if users_repo.is_blocked(uid):
            return None
    return uid


def resolve_uid_from_webapp(
    telegram_id: Optional[str | int] = None,
    token: Optional[str] = None,
    init_data: Optional[str] = None,
) -> Optional[int]:
    """
    Session token first; fallback to Telegram WebApp initData (export after redeploy).
    """
    uid = resolve_uid(
        str(telegram_id) if telegram_id is not None else None,
        token,
    )
    if uid:
        return uid

    raw_init = (init_data or "").strip()
    if not raw_init:
        return None

    from config.settings import settings
    from core.telegram_auth import extract_telegram_user_id, validate_init_data

    if not settings.bot_token:
        return None

    validated = validate_init_data(
        raw_init,
        settings.bot_token,
        max_age_seconds=settings.init_data_max_age_seconds,
    )
    if not validated:
        return None

    verified_id = extract_telegram_user_id(validated)
    if not verified_id:
        return None

    if telegram_id is not None and str(telegram_id).strip().isdigit():
        if int(telegram_id) != int(verified_id):
            return None

    uid = int(verified_id)
    if not is_admin(uid):
        from database.repositories import users as users_repo

        if users_repo.is_blocked(uid):
            return None
    return uid


def is_admin(telegram_id: int | None) -> bool:
    if not telegram_id:
        return False
    from config.settings import settings

    return int(telegram_id) in settings.admin_user_ids
