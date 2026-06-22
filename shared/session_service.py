"""WebApp session tokens — Redis primary, JSON file fallback."""
from __future__ import annotations

import json
import logging
import os
import secrets
import time
from typing import Optional

from core.redis_client import get_sync_redis, is_redis_live, key

from config.paths import sessions_file, temp_dir

logger = logging.getLogger(__name__)

SESSION_TTL = 60 * 60 * 24

_cache: dict[str, dict] = {}
_loaded = False


def _session_path() -> str:
    return str(sessions_file())


def _load_file() -> None:
    global _cache, _loaded
    if _loaded:
        return
    path = _session_path()
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                _cache = json.load(f)
    except Exception as exc:
        logger.warning("session file load error: %s", exc)
        _cache = {}
    _loaded = True


def _save_file() -> None:
    path = _session_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_cache, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.warning("session file save error: %s", exc)


def _session_payload(
    telegram_id: int | str,
    first_name: str,
    username: str,
    photo_url: str,
) -> dict:
    now = time.time()
    return {
        "telegram_id": str(telegram_id),
        "first_name": first_name,
        "username": username,
        "photo_url": photo_url,
        "created_at": now,
        "last_active": now,
    }


def _redis_get_session(token: str) -> Optional[dict]:
    r = get_sync_redis()
    if not r:
        return None
    raw = r.get(key(f"session:{token}"))
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _redis_save_session(token: str, data: dict, uid: str) -> None:
    r = get_sync_redis()
    if not r:
        return
    pipe = r.pipeline()
    pipe.setex(key(f"session:{token}"), SESSION_TTL, json.dumps(data, ensure_ascii=False))
    pipe.setex(key(f"session_uid:{uid}"), SESSION_TTL, token)
    pipe.execute()


def create_session(
    telegram_id: int | str,
    first_name: str = "",
    username: str = "",
    photo_url: str = "",
) -> str:
    uid = str(telegram_id)

    if is_redis_live():
        r = get_sync_redis()
        if r:
            existing = r.get(key(f"session_uid:{uid}"))
            if existing:
                token = str(existing)
                sess = _redis_get_session(token) or _session_payload(uid, first_name, username, photo_url)
                sess["last_active"] = time.time()
                if first_name:
                    sess["first_name"] = first_name
                if username:
                    sess["username"] = username
                if photo_url:
                    sess["photo_url"] = photo_url
                _redis_save_session(token, sess, uid)
                return token
            token = secrets.token_hex(16)
            _redis_save_session(token, _session_payload(uid, first_name, username, photo_url), uid)
            logger.info("Session created (redis) telegram_id=%s", uid)
            return token

    _load_file()
    for tok, sess in _cache.items():
        if sess.get("telegram_id") == uid:
            sess["last_active"] = time.time()
            if first_name:
                sess["first_name"] = first_name
            if username:
                sess["username"] = username
            if photo_url:
                sess["photo_url"] = photo_url
            _save_file()
            return tok

    token = secrets.token_hex(16)
    _cache[token] = _session_payload(uid, first_name, username, photo_url)
    _save_file()
    logger.info("Session created (file) telegram_id=%s", uid)
    return token


def resolve_session(token: str) -> Optional[dict]:
    if is_redis_live():
        sess = _redis_get_session(token)
        if not sess:
            return None
        if time.time() - float(sess.get("created_at", 0)) > SESSION_TTL:
            invalidate(token)
            return None
        sess["last_active"] = time.time()
        uid = str(sess.get("telegram_id", ""))
        _redis_save_session(token, sess, uid)
        return sess

    _load_file()
    sess = _cache.get(token)
    if not sess:
        return None
    if time.time() - float(sess.get("created_at", 0)) > SESSION_TTL:
        _cache.pop(token, None)
        _save_file()
        return None
    sess["last_active"] = time.time()
    return sess


def resolve_telegram_id(token: str) -> Optional[str]:
    sess = resolve_session(token)
    return sess["telegram_id"] if sess else None


def get_session_by_telegram_id(telegram_id: int | str) -> Optional[dict]:
    uid = str(telegram_id)
    if is_redis_live():
        r = get_sync_redis()
        if r:
            token = r.get(key(f"session_uid:{uid}"))
            if token:
                return resolve_session(str(token))
            return None

    _load_file()
    for sess in _cache.values():
        if sess.get("telegram_id") == uid:
            return sess
    return None


def invalidate(token: str) -> None:
    if is_redis_live():
        r = get_sync_redis()
        if r:
            sess = _redis_get_session(token)
            pipe = r.pipeline()
            pipe.delete(key(f"session:{token}"))
            if sess:
                pipe.delete(key(f"session_uid:{sess.get('telegram_id', '')}"))
            pipe.execute()
            return

    _load_file()
    _cache.pop(token, None)
    _save_file()


def touch(token: str) -> None:
    sess = resolve_session(token)
    if not sess:
        return
    if is_redis_live():
        _redis_save_session(token, sess, str(sess.get("telegram_id", "")))
    else:
        _save_file()
