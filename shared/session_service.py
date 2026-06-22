"""
Session Service — Unified Website ↔ Telegram Identity Bridge
─────────────────────────────────────────────────────────────
Every user who opens the website gets a short-lived auth token
tied to their Telegram identity. This token is stored in
sessionStorage on the browser AND recorded here, so every
backend API call can resolve the real Telegram user without
requiring the bot to be "active" at that moment.

Token flow:
  1. User opens bot → presses "Appni ochish" button
  2. Bot embeds ?telegram_id=<uid> in the WebApp URL       ← already done
  3. index.html reads tg.initDataUnsafe.user and stores it
     in sessionStorage under MULTIPLE keys for resilience
  4. Every sub-page reads from sessionStorage as fallback
  5. Every /api/* call accepts telegram_id as optional Form field
  6. This service provides server-side validation helpers

ARCHITECTURE NOTE:
  We intentionally do NOT implement a database here — the
  project stores data in JSON files.  The session file is a
  lightweight in-memory + file cache with TTL cleanup.
"""

import os
import json
import time
import secrets
import logging
from typing import Optional

logger = logging.getLogger(__name__)

SESSION_FILE = "temp/sessions.json"
SESSION_TTL  = 60 * 60 * 24  # 24-hour TTL per session

# ── in-memory cache (avoids disk reads on every API call) ──────────────────
_cache: dict[str, dict] = {}
_loaded = False


def _load() -> None:
    global _cache, _loaded
    if _loaded:
        return
    os.makedirs("temp", exist_ok=True)
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                _cache = json.load(f)
    except Exception as e:
        logger.warning(f"session_service load error: {e}")
        _cache = {}
    _loaded = True


def _save() -> None:
    os.makedirs("temp", exist_ok=True)
    try:
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(_cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"session_service save error: {e}")


def _evict_expired() -> None:
    """Remove sessions older than TTL (called lazily on write)."""
    now = time.time()
    expired = [tok for tok, s in _cache.items()
               if now - s.get("created_at", 0) > SESSION_TTL]
    for tok in expired:
        del _cache[tok]


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def create_session(telegram_id: int | str,
                   first_name: str = "",
                   username: str = "",
                   photo_url: str = "") -> str:
    """
    Create (or refresh) a session for a Telegram user.
    Returns a 32-character hex token that the frontend stores.
    """
    _load()
    _evict_expired()

    uid = str(telegram_id)

    # Reuse existing valid token for the same user
    for tok, sess in _cache.items():
        if sess.get("telegram_id") == uid:
            sess["last_active"] = time.time()
            sess["first_name"] = first_name or sess.get("first_name", "")
            sess["username"]   = username   or sess.get("username", "")
            if photo_url:
                sess["photo_url"] = photo_url
            _save()
            return tok

    token = secrets.token_hex(16)  # 32-char hex
    _cache[token] = {
        "telegram_id" : uid,
        "first_name"  : first_name,
        "username"    : username,
        "photo_url"   : photo_url,
        "created_at"  : time.time(),
        "last_active" : time.time(),
    }
    _save()
    logger.info(f"Session created for telegram_id={uid}")
    return token


def resolve_session(token: str) -> Optional[dict]:
    """
    Given a token, return the session dict (with telegram_id etc.)
    or None if the token is invalid / expired.
    """
    _load()
    sess = _cache.get(token)
    if not sess:
        return None
    if time.time() - sess.get("created_at", 0) > SESSION_TTL:
        del _cache[token]
        _save()
        return None
    sess["last_active"] = time.time()
    return sess


def resolve_telegram_id(token: str) -> Optional[str]:
    """Shorthand: return just the telegram_id for an active token."""
    sess = resolve_session(token)
    return sess["telegram_id"] if sess else None


def get_session_by_telegram_id(telegram_id: int | str) -> Optional[dict]:
    """Find active session for a given Telegram user (reverse lookup)."""
    _load()
    uid = str(telegram_id)
    for sess in _cache.values():
        if sess.get("telegram_id") == uid:
            return sess
    return None


def invalidate(token: str) -> None:
    """Explicitly invalidate a session (logout)."""
    _load()
    _cache.pop(token, None)
    _save()


def touch(token: str) -> None:
    """Refresh last_active timestamp without full validation."""
    _load()
    if token in _cache:
        _cache[token]["last_active"] = time.time()
