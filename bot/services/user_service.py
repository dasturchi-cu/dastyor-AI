"""
User Service (CRM) - Advanced
Tracks full user lifecycle, bans, and granular stats.
"""
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

PROFILES_FILE = "user_profiles.json"
profiles_cache = {}

def _load_profiles():
    global profiles_cache
    if profiles_cache: return profiles_cache
    if not os.path.exists(PROFILES_FILE): return {}
    try:
        with open(PROFILES_FILE, "r", encoding="utf-8") as f:
            profiles_cache = json.load(f)
            return profiles_cache
    except:
        return {}

def _save_profiles():
    global profiles_cache
    try:
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(profiles_cache, f, ensure_ascii=False, indent=2)
    except: pass

def get_user_profile(user_id):
    data = _load_profiles()
    return data.get(str(user_id))

def get_all_profiles():
    return _load_profiles()

def track_user_activity(user, command=None):
    """
    Called on every update to track activity.
    Also handles initial registration.
    """
    if not user: return
    
    uid = str(user.id)
    data = _load_profiles()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # If blocked, do not update activity (optional logic)
    # But usually we still want to track they tried to use it
    
    if uid not in data:
        # Register New User
        data[uid] = {
            "id": user.id,
            "first_name": user.first_name,
            "username": user.username,
            "joined_at": now_str,
            "last_active": now_str,
            "activtiy_count": 1,
            "files_processed": 0,
            "sessions": 1,
            "is_banned": False,
            "ban_reason": None,
            "ban_date": None,
            "blocked_bot": False, # New field: User blocked bot
            "premium_history": []
        }
    else:
        # Update Existing
        p = data[uid]
        p["first_name"] = user.first_name
        p["username"] = user.username
        p["last_active"] = now_str
        p["activtiy_count"] = p.get("activtiy_count", 0) + 1
        p["blocked_bot"] = False # If they are active, they haven't blocked bot
        
        if command == "start":
            p["sessions"] = p.get("sessions", 0) + 1
        
    _save_profiles()

def set_user_blocked_bot(user_id, blocked=True):
    """Track if user blocked the bot"""
    data = _load_profiles()
    uid = str(user_id)
    if uid in data:
        data[uid]["blocked_bot"] = blocked
        _save_profiles()

def increment_file_count(user_id, service_name=None):
    """Increment file processed count"""
    data = _load_profiles()
    uid = str(user_id)
    if uid in data:
        data[uid]["files_processed"] = data[uid].get("files_processed", 0) + 1
        data[uid]["last_service"] = service_name
        _save_profiles()

def set_ban_status(user_id, is_banned=True, reason=None):
    """Ban or Unban user (Admin action)"""
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

def is_user_banned(user_id):
    """Check if banned by admin"""
    data = _load_profiles()
    return data.get(str(user_id), {}).get("is_banned", False)

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
