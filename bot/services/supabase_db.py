"""
Supabase DB — Ma'lumotlar bazasi bilan ishlash
SUPABASE_URL va SUPABASE_ANON_KEY bo'lsa ishlatiladi.
"""
import os
import logging
from datetime import datetime, date
from typing import Optional

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        return None
    try:
        from supabase import create_client
        _client = create_client(url, key)
        logger.info("Supabase client initialized")
        return _client
    except Exception as e:
        logger.warning(f"Supabase init failed: {e}")
        return None


def has_db() -> bool:
    return _get_client() is not None


# ── users ────────────────────────────────────────────────────────────────────
def db_get_user(user_id: int | str) -> Optional[dict]:
    c = _get_client()
    if not c:
        return None
    try:
        r = c.table("users").select("*").eq("id", int(user_id)).execute()
        rows = r.data
        if not rows:
            return None
        row = rows[0]
        return {
            "id": row["id"],
            "first_name": row.get("first_name", ""),
            "username": row.get("username"),
            "chat_id": row.get("chat_id"),
            "joined_at": row.get("joined_at"),
            "last_active": row.get("last_active"),
            "activtiy_count": row.get("activity_count", 0),
            "activity_count": row.get("activity_count", 0),
            "files_processed": row.get("files_processed", 0),
            "sessions": row.get("sessions", 0),
            "lang": row.get("lang", "uz_lat"),
            "is_banned": row.get("is_banned", False),
            "ban_reason": row.get("ban_reason"),
            "ban_date": row.get("ban_date"),
            "blocked_bot": row.get("blocked_bot", False),
            "last_service": row.get("last_service"),
        }
    except Exception as e:
        logger.error(f"db_get_user: {e}")
        return None


def db_upsert_user(user_id: int, first_name: str = "", username: str = None,
                   chat_id: int = None, command: str = None) -> bool:
    c = _get_client()
    if not c:
        return False
    try:
        now = datetime.utcnow().isoformat()
        r = c.table("users").select("id,sessions").eq("id", user_id).execute()
        if r.data:
            upd = {"first_name": first_name or "", "last_active": now}
            if username is not None:
                upd["username"] = username
            if chat_id is not None:
                upd["chat_id"] = chat_id
            if command == "start":
                sess = r.data[0].get("sessions", 0) or 0
                upd["sessions"] = sess + 1
            c.table("users").update(upd).eq("id", user_id).execute()
        else:
            c.table("users").insert({
                "id": user_id,
                "first_name": first_name or "",
                "username": username or "",
                "chat_id": chat_id or user_id,
                "interaction_count": 1,
                "activity_count": 1,
                "sessions": 1 if command == "start" else 0,
            }).execute()
        return True
    except Exception as e:
        logger.error(f"db_upsert_user: {e}")
        return False


def db_update_user_field(user_id: int, **kwargs) -> bool:
    c = _get_client()
    if not c:
        return False
    try:
        c.table("users").update(kwargs).eq("id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"db_update_user_field: {e}")
        return False


def db_increment_files(user_id: int, service_name: str = None) -> bool:
    c = _get_client()
    if not c:
        return False
    try:
        r = c.table("users").select("files_processed").eq("id", user_id).execute()
        if r.data:
            count = r.data[0].get("files_processed", 0) + 1
            upd = {"files_processed": count}
            if service_name:
                upd["last_service"] = service_name
            c.table("users").update(upd).eq("id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"db_increment_files: {e}")
        return False


# ── daily_usage ──────────────────────────────────────────────────────────────
def db_get_usage(user_id: int) -> int:
    c = _get_client()
    if not c:
        return 0
    try:
        today = date.today().isoformat()
        r = c.table("daily_usage").select("count").eq("user_id", user_id).eq("usage_date", today).execute()
        if r.data:
            return r.data[0].get("count", 0)
        return 0
    except Exception as e:
        logger.error(f"db_get_usage: {e}")
        return 0


def db_increment_usage(user_id: int) -> int:
    c = _get_client()
    if not c:
        return 0
    try:
        today = date.today().isoformat()
        r = c.table("daily_usage").select("id,count").eq("user_id", user_id).eq("usage_date", today).execute()
        if r.data:
            new_count = r.data[0].get("count", 0) + 1
            c.table("daily_usage").update({"count": new_count}).eq("id", r.data[0]["id"]).execute()
            return new_count
        c.table("daily_usage").insert({"user_id": user_id, "usage_date": today, "count": 1}).execute()
        return 1
    except Exception as e:
        logger.error(f"db_increment_usage: {e}")
        return 0


# ── bot_settings ─────────────────────────────────────────────────────────────
def db_get_daily_limit() -> Optional[int]:
    c = _get_client()
    if not c:
        return None
    try:
        r = c.table("bot_settings").select("daily_limit").eq("id", 1).execute()
        if r.data:
            return r.data[0].get("daily_limit", 10)
        return 10
    except Exception as e:
        logger.error(f"db_get_daily_limit: {e}")
        return None


# ── premium (premium_subscriptions) ──────────────────────────────────────────
def db_is_premium(user_id: int) -> bool:
    c = _get_client()
    if not c:
        return False
    try:
        now = datetime.utcnow().isoformat()
        r = c.table("premium_subscriptions").select("id").eq("user_id", user_id).gte("end_date", now).execute()
        return bool(r.data)
    except Exception as e:
        logger.error(f"db_is_premium: {e}")
        return False


# ── get_all_users (for CRM / stats) ──────────────────────────────────────────
def db_get_all_users() -> dict:
    c = _get_client()
    if not c:
        return {}
    try:
        r = c.table("users").select("*").execute()
        out = {}
        for row in r.data or []:
            uid = str(row["id"])
            out[uid] = {
                "id": row["id"],
                "first_name": row.get("first_name", ""),
                "username": row.get("username"),
                "chat_id": row.get("chat_id"),
                "joined_at": row.get("joined_at"),
                "last_active": row.get("last_active"),
                "activtiy_count": row.get("activity_count", 0),
                "activity_count": row.get("activity_count", 0),
                "files_processed": row.get("files_processed", 0),
                "sessions": row.get("sessions", 0),
                "lang": row.get("lang", "uz_lat"),
                "is_banned": row.get("is_banned", False),
                "ban_reason": row.get("ban_reason"),
                "ban_date": row.get("ban_date"),
                "blocked_bot": row.get("blocked_bot", False),
                "last_service": row.get("last_service"),
            }
        return out
    except Exception as e:
        logger.error(f"db_get_all_users: {e}")
        return {}
