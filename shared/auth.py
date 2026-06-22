"""Resolve Telegram user from session token or query param."""
from __future__ import annotations

from typing import Optional

from shared.session_service import resolve_telegram_id


def resolve_uid(telegram_id: Optional[str] = None, token: Optional[str] = None) -> Optional[int]:
    if token:
        uid = resolve_telegram_id(token)
        if uid and str(uid).isdigit():
            return int(uid)
    if telegram_id and str(telegram_id).strip().isdigit():
        return int(telegram_id)
    return None
