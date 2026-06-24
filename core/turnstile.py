"""Cloudflare Turnstile server-side verification."""
from __future__ import annotations

import logging

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile(token: str | None, *, remote_ip: str | None = None) -> bool:
    secret = (settings.turnstile_secret_key or "").strip()
    if not secret:
        return True
    if not (token or "").strip():
        return False
    payload: dict[str, str] = {"secret": secret, "response": token.strip()}
    if remote_ip:
        payload["remoteip"] = remote_ip
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_VERIFY_URL, data=payload)
            resp.raise_for_status()
            data = resp.json()
            return bool(data.get("success"))
    except Exception as exc:
        logger.warning("Turnstile verify failed: %s", exc)
        return False
