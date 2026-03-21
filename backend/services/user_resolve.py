"""Resolve Telegram user id from session token or legacy query param."""
from __future__ import annotations

import os
from typing import Optional


def safe_filename_part(name: str, fallback: str) -> str:
    base = os.path.basename(name or "").strip()
    if not base:
        return fallback
    cleaned = "".join(ch for ch in base if ch.isalnum() or ch in ("-", "_", ".", " ")).strip()
    return cleaned or fallback


def resolve_telegram_uid(
    telegram_id_param: Optional[str] = None,
    session_token: Optional[str] = None,
) -> Optional[str]:
    if session_token:
        from bot.services.session_service import resolve_telegram_id

        uid = resolve_telegram_id(session_token)
        if uid:
            return uid
    if telegram_id_param and telegram_id_param.strip().isdigit():
        return telegram_id_param.strip()
    return None
