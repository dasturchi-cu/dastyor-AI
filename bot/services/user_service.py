"""
User Service (CRM) - Advanced
Tracks full user lifecycle, bans, granular stats.
Uses Supabase when SUPABASE_URL is set, else JSON file.
"""
import json
import os
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)

PROFILES_FILE = "user_profiles.json"
profiles_cache = {}
# Supabase: har xabarda yozmaslik — sekinlik va 429 oldini olish (0 = har safar)
_SUPABASE_USER_SYNC_INTERVAL = float(os.getenv("USER_SUPABASE_SYNC_SECONDS", "35") or "35")
_LAST_SUPABASE_USER_SYNC: dict[int, float] = {}

def _load_profiles():
    global profiles_cache
    if profiles_cache: return profiles_cache
    if not os.path.exists(PROFILES_FILE): return {}
    try:
        with open(PROFILES_FILE, "r", encoding="utf-8") as f:
            profiles_cache = json.load(f)
            return profiles_cache
    except Exception:
        return {}

def _save_profiles():
    try:
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(profiles_cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def get_user_profile(user_id):
    try:
        from bot.services.supabase_db import has_db, db_get_user
        if has_db():
            p = db_get_user(user_id)
            if p:
                return p
    except Exception as e:
        logger.debug(f"Supabase get_user_profile fallback: {e}")
    data = _load_profiles()
    return data.get(str(user_id))

def get_all_profiles():
    try:
        from bot.services.supabase_db import has_db, db_get_all_users
        if has_db():
            return db_get_all_users()
    except Exception as e:
        logger.debug(f"Supabase get_all_profiles fallback: {e}")
    return _load_profiles()

def track_user_activity(user, command=None, chat_id=None):
    """
    Called on every update to track activity.
    Also handles initial registration.

    chat_id: shaxsiy chat uchun Telegram chat id. None bo'lsa user.id.
    """
    if not user:
        return
    uid_int = int(user.id)
    cid = int(chat_id) if chat_id is not None else uid_int
    now_ts = time.time()
    force_supa = (
        command in ("start", "web_auth")
        or _SUPABASE_USER_SYNC_INTERVAL <= 0
    )
    skip_supa = False
    if not force_supa and _SUPABASE_USER_SYNC_INTERVAL > 0:
        last = _LAST_SUPABASE_USER_SYNC.get(uid_int, 0.0)
        if now_ts - last < _SUPABASE_USER_SYNC_INTERVAL:
            skip_supa = True

    try:
        from bot.services.supabase_db import has_db, db_upsert_user

        if has_db() and not skip_supa:
            db_upsert_user(
                uid_int,
                first_name=user.first_name or "",
                username=user.username,
                chat_id=cid,
                command=command,
            )
            _LAST_SUPABASE_USER_SYNC[uid_int] = now_ts
    except Exception as e:
        logger.debug(f"Supabase track_user_activity fallback: {e}")

    uid = str(user.id)
    data = _load_profiles()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if uid not in data:
        # Register New User
        data[uid] = {
            "id": user.id,
            "first_name": user.first_name,
            "username": user.username,
            "chat_id": cid,
            "joined_at": now_str,
            "last_active": now_str,
            "activtiy_count": 1,
            "files_processed": 0,
            "sessions": 1,
            "is_banned": False,
            "ban_reason": None,
            "ban_date": None,
            "blocked_bot": False, # New field: User blocked bot
            "lang": "uz_lat",
            "premium_history": []
        }
    else:
        # Update Existing
        p = data[uid]
        p["first_name"] = user.first_name
        p["username"] = user.username
        p["chat_id"] = cid
        p["last_active"] = now_str
        p["activtiy_count"] = p.get("activtiy_count", 0) + 1
        p["blocked_bot"] = False # If they are active, they haven't blocked bot
        
        if command == "start":
            p["sessions"] = p.get("sessions", 0) + 1
        
    _save_profiles()

def set_user_blocked_bot(user_id, blocked=True):
    """Track if user blocked the bot"""
    try:
        from bot.services.supabase_db import has_db, db_update_user_field
        if has_db():
            db_update_user_field(int(user_id), blocked_bot=blocked)
            return
    except Exception as e:
        logger.debug(f"Supabase set_user_blocked_bot fallback: {e}")
    data = _load_profiles()
    uid = str(user_id)
    if uid in data:
        data[uid]["blocked_bot"] = blocked
        _save_profiles()

def increment_file_count(user_id, service_name=None):
    """Increment file processed count"""
    try:
        from bot.services.supabase_db import has_db, db_increment_files
        if has_db():
            db_increment_files(int(user_id), service_name)
            return
    except Exception as e:
        logger.debug(f"Supabase increment_file_count fallback: {e}")
    data = _load_profiles()
    uid = str(user_id)
    if uid in data:
        data[uid]["files_processed"] = data[uid].get("files_processed", 0) + 1
        data[uid]["last_service"] = service_name
        _save_profiles()


def record_service_completion(user_id, service_name=None):
    """Muvaffaqiyatli xizmatdan keyin: kunlik hisob + files_processed."""
    from bot.services.usage_tracker import increment_usage

    increment_usage(int(user_id), service_name or "service")
    increment_file_count(int(user_id), service_name)

def set_ban_status(user_id, is_banned=True, reason=None):
    """Ban or Unban user (Admin action)"""
    try:
        from bot.services.supabase_db import has_db, db_update_user_field, db_get_user
        if has_db():
            p = db_get_user(user_id)
            if p:
                from datetime import datetime as dt
                db_update_user_field(
                    int(user_id),
                    is_banned=is_banned,
                    ban_reason=reason,
                    ban_date=dt.utcnow().isoformat() if is_banned else None
                )
                return True
            return False
    except Exception as e:
        logger.debug(f"Supabase set_ban_status fallback: {e}")
    data = _load_profiles()
    uid = str(user_id)
    if uid in data:
        data[uid]["is_banned"] = is_banned
        if is_banned:
            data[uid]["ban_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data[uid]["ban_reason"] = reason
        else:
            data[uid]["ban_date"] = None
            data[uid]["ban_reason"] = None
        _save_profiles()
        return True
    return False


def save_chat_id(user_id, chat_id):
    """
    Update (or set) the Telegram chat_id for a user.
    Called from /start handler and /api/auth endpoint.
    """
    try:
        from bot.services.supabase_db import has_db, db_upsert_user, db_get_user
        if has_db():
            p = db_get_user(user_id)
            if p:
                from bot.services.supabase_db import db_update_user_field
                db_update_user_field(int(user_id), chat_id=int(chat_id))
            else:
                db_upsert_user(int(user_id), first_name="", chat_id=int(chat_id))
            return
    except Exception as e:
        logger.debug(f"Supabase save_chat_id fallback: {e}")
    data = _load_profiles()
    uid = str(user_id)
    if uid in data:
        data[uid]["chat_id"] = int(chat_id)
        _save_profiles()
    else:
        # User not yet tracked – create a minimal profile so we can
        # deliver files even before they ever sent the bot a message.
        data[uid] = {
            "id": int(user_id),
            "first_name": "",
            "username": "",
            "chat_id": int(chat_id),
            "joined_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_active": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "activtiy_count": 0,
            "files_processed": 0,
            "sessions": 0,
            "is_banned": False,
            "ban_reason": None,
            "ban_date": None,
            "blocked_bot": False,
            "lang": "uz_lat",
            "premium_history": []
        }
        _save_profiles()

def get_user_lang(user_id) -> str:
    p = get_user_profile(user_id)
    return (p or {}).get("lang", "uz_lat")

def get_chat_id(user_id) -> int | None:
    """
    Return the Telegram chat_id for a user_id.
    Falls back to user_id itself (valid for private chats).
    """
    p = get_user_profile(user_id)
    if p:
        return p.get("chat_id") or (int(user_id) if str(user_id).isdigit() else None)
    return int(user_id) if str(user_id).isdigit() else None

def is_user_banned(user_id):
    """Check if banned by admin"""
    p = get_user_profile(user_id)
    return (p or {}).get("is_banned", False)

def log_premium_transaction(user_id, days, admin_id="Admin"):
    """Log premium purchase"""
    data = _load_profiles()
    uid = str(user_id)
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "days": days,
        "given_by": admin_id
    }
    if uid in data:
        if "premium_history" not in data[uid]: data[uid]["premium_history"] = []
        data[uid]["premium_history"].append(entry)
        _save_profiles()

def save_pending_oby_data(user_id, data: dict):
    """Save AI-extracted obyektivka data (Supabase + mahalliy JSON fallback)."""
    uid = str(user_id)
    try:
        from bot.services.supabase_db import has_db, db_save_pending_oby

        if has_db():
            db_save_pending_oby(int(user_id), data)
    except Exception as e:
        logger.debug("save_pending_oby_data Supabase: %s", e)

    profiles = _load_profiles()
    if uid not in profiles:
        profiles[uid] = {}
    profiles[uid]["pending_oby_data"] = data
    _save_profiles()

def get_pending_oby_data(user_id):
    """Return saved pending obyektivka data or None."""
    try:
        from bot.services.supabase_db import has_db, db_get_pending_oby

        if has_db():
            row = db_get_pending_oby(int(user_id))
            if row:
                return row
    except Exception as e:
        logger.debug("get_pending_oby_data Supabase: %s", e)
    profiles = _load_profiles()
    return profiles.get(str(user_id), {}).get("pending_oby_data")

def clear_pending_oby_data(user_id):
    """Remove pending obyektivka data after use."""
    try:
        from bot.services.supabase_db import has_db, db_clear_pending_oby

        if has_db():
            db_clear_pending_oby(int(user_id))
    except Exception as e:
        logger.debug("clear_pending_oby_data Supabase: %s", e)
    profiles = _load_profiles()
    uid = str(user_id)
    if uid in profiles and "pending_oby_data" in profiles[uid]:
        del profiles[uid]["pending_oby_data"]
        _save_profiles()

def get_daily_crm_stats():
    """Get advanced daily stats"""
    data = _load_profiles()
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    stats = {
        "new_users": 0,
        "active_users": 0,
        "premium_sales": 0,
        "total_files_today": 0 # Hard to track without daily bucket, but we can try approximate
    }
    
    for p in data.values():
        # New Users
        if p.get("joined_at", "").startswith(today_str):
            stats["new_users"] += 1
            
        # Active Users
        if p.get("last_active", "").startswith(today_str):
            stats["active_users"] += 1
            
        # Premium Sales Today
        for h in p.get("premium_history", []):
            if h.get("date", "").startswith(today_str):
                stats["premium_sales"] += 1
                
    return stats
