"""Telegram WebApp initData validation (HMAC-SHA256)."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any
from urllib.parse import parse_qsl

logger = logging.getLogger(__name__)


def validate_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = 86_400,
) -> dict[str, Any] | None:
    """
    Validate Telegram WebApp initData per official spec.
    Returns parsed payload with `user` dict on success, else None.
    """
    raw = (init_data or "").strip()
    token = (bot_token or "").strip()
    if not raw or not token:
        return None

    try:
        pairs = dict(parse_qsl(raw, keep_blank_values=True))
    except ValueError:
        return None

    received_hash = pairs.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", token.encode("utf-8"), hashlib.sha256).digest()
    computed = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed, received_hash):
        logger.warning("initData HMAC mismatch")
        return None

    try:
        auth_date = int(pairs.get("auth_date") or 0)
    except (TypeError, ValueError):
        auth_date = 0

    if auth_date and max_age_seconds > 0:
        if time.time() - auth_date > max_age_seconds:
            logger.warning("initData expired auth_date=%s", auth_date)
            return None

    user: dict[str, Any] | None = None
    user_raw = pairs.get("user")
    if user_raw:
        try:
            parsed_user = json.loads(user_raw)
            if isinstance(parsed_user, dict):
                user = parsed_user
        except json.JSONDecodeError:
            return None

    return {"user": user, "auth_date": auth_date, "raw": pairs}


def extract_telegram_user_id(validated: dict[str, Any] | None) -> int | None:
    if not validated:
        return None
    user = validated.get("user")
    if not isinstance(user, dict):
        return None
    uid = user.get("id")
    if uid is None:
        return None
    try:
        return int(uid)
    except (TypeError, ValueError):
        return None
