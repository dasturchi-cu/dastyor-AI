"""
Settings Service (Enhanced)
Manages dynamic bot settings including detailed Premium User management.
"""
import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Har xabarda Supabase bot_settings so‘rovi — qisqa TTL kesh (maintenance tekshiruvi).
_MAINT_CACHE_TTL = float(os.getenv("MAINTENANCE_MODE_CACHE_TTL_SECONDS", "15") or "15")
_maint_lock = threading.Lock()
_maint_cache = {"ts": 0.0, "value": None}


def invalidate_maintenance_mode_cache() -> None:
    with _maint_lock:
        _maint_cache["ts"] = 0.0
        _maint_cache["value"] = None


def _read_maintenance_mode_uncached() -> bool:
    try:
        from bot.services.supabase_db import has_db, db_get_maintenance_mode

        if has_db():
            mode = db_get_maintenance_mode()
            if mode is not None:
                return bool(mode)
    except Exception as e:
        logger.debug(f"Supabase get_maintenance_mode fallback: {e}")
    return bool(_load_settings().get("maintenance_mode", False))

SETTINGS_FILE = "bot_settings.json"

DEFAULT_SETTINGS = {
    "channels": {},
    "premium_users": {}, # Changed from list to dict: { "user_id": { "name": "Name", "username": "@user", "end_date": "YYYY-MM-DD" } }
    "daily_limit": 10,
    "maintenance_mode": False
}

def _load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
            # Migrate old list format to new dict format if needed
            if isinstance(data.get("premium_users"), list):
                new_premiums = {}
                for uid in data["premium_users"]:
                    # Give legacy users unlimited time (e.g. 10 years)
                    new_premiums[str(uid)] = {
                        "name": "Unknown",
                        "username": "Unknown",
                        "end_date": "2030-01-01"
                    }
                data["premium_users"] = new_premiums
                _save_settings(data)
                
            # Merge defaults
            for key, val in DEFAULT_SETTINGS.items():
                if key not in data:
                    data[key] = val
            return data
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        return DEFAULT_SETTINGS.copy()

def _save_settings(data):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving settings: {e}")

# === CHANNELS ===
def get_channels():
    return _load_settings()["channels"]

def add_channel(channel_id, channel_name):
    data = _load_settings()
    data["channels"][str(channel_id)] = channel_name
    _save_settings(data)

def remove_channel(channel_id):
    data = _load_settings()
    if str(channel_id) in data["channels"]:
        del data["channels"][str(channel_id)]
        _save_settings(data)

# === PREMIUM ===
def get_premium_users_full():
    """Return full dict of premium users"""
    return _load_settings()["premium_users"]

def add_premium(user_id, days=30, name="Unknown", username="Unknown"):
    """Add or extend premium for user"""
    data = _load_settings()
    uid = str(user_id)
    
    start_date = datetime.now()
    # If already exists and active, extend from current end_date
    if uid in data["premium_users"]:
        current_end = datetime.strptime(data["premium_users"][uid]["end_date"], "%Y-%m-%d")
        if current_end > start_date:
            start_date = current_end
            
    end_date = start_date + timedelta(days=days)
    end_str = end_date.strftime("%Y-%m-%d")
    
    data["premium_users"][uid] = {
        "name": name,
        "username": username,
        "end_date": end_str
    }
    _save_settings(data)
    return end_str

def remove_premium(user_id):
    data = _load_settings()
    uid = str(user_id)
    if uid in data["premium_users"]:
        del data["premium_users"][uid]
        _save_settings(data)
        return True
    return False

def is_premium(user_id):
    """Check if user has ACTIVE premium"""
    try:
        from bot.services.supabase_db import has_db, db_is_premium
        if has_db():
            return db_is_premium(int(user_id))
    except Exception as e:
        logger.debug(f"Supabase is_premium fallback: {e}")
    data = _load_settings()
    uid = str(user_id)
    
    if uid not in data["premium_users"]:
        return False
        
    user_data = data["premium_users"][uid]
    try:
        end_date = datetime.strptime(user_data["end_date"], "%Y-%m-%d")
        if end_date >= datetime.now():
            return True
        else:
            # Expired - optionally remove? Let's keep for history or cleanup later
            return False
    except:
        return False


def get_premium_record(user_id):
    """Return premium record dict for user or None."""
    data = _load_settings()
    return data.get("premium_users", {}).get(str(user_id))


def get_premium_status(user_id) -> str:
    """
    Premium status:
    - active
    - expired
    - none
    """
    rec = get_premium_record(user_id)
    if not rec:
        return "none"
    try:
        end_date = datetime.strptime(rec.get("end_date", ""), "%Y-%m-%d")
        return "active" if end_date >= datetime.now() else "expired"
    except Exception:
        return "none"


def get_premium_expiry(user_id) -> str | None:
    rec = get_premium_record(user_id)
    if not rec:
        return None
    return rec.get("end_date")


def get_active_plan_code(user_id) -> str:
    """
    Foydalanuvchining hozirgi tarifi: 'free' | 'standard' | 'premium'.
    DBda faol obuna bo'lsa plan_type; JSON (legacy) faqat premium sifatida.
    """
    uid = int(user_id)
    try:
        from bot.services.supabase_db import has_db, db_get_active_plan_type
        if has_db():
            pt = db_get_active_plan_type(uid)
            if pt in ("standard", "premium"):
                return pt
    except Exception as e:
        logger.debug("get_active_plan_code db: %s", e)
    if is_premium(uid):
        return "premium"
    return "free"


def get_active_subscription_expires_display(user_id) -> str | None:
    """Faol obuna tugash sanasi (YYYY-MM-DD) yoki None."""
    uid = int(user_id)
    try:
        from bot.services.supabase_db import has_db, db_get_active_subscription_expiry_raw
        if has_db():
            raw = db_get_active_subscription_expiry_raw(uid)
            if raw:
                return raw[:10] if len(raw) >= 10 else raw
    except Exception as e:
        logger.debug("get_active_subscription_expires_display db: %s", e)
    return get_premium_expiry(user_id)


# === CONFIG ===
def get_daily_limit():
    try:
        from bot.services.supabase_db import has_db, db_get_daily_limit
        if has_db():
            limit = db_get_daily_limit()
            if limit is not None:
                return limit
    except Exception as e:
        logger.debug(f"Supabase get_daily_limit fallback: {e}")
    return _load_settings().get("daily_limit", 10)

def set_daily_limit(limit):
    data = _load_settings()
    data["daily_limit"] = int(limit)
    _save_settings(data)


def get_maintenance_mode() -> bool:
    now = time.monotonic()
    with _maint_lock:
        hit_ts = float(_maint_cache.get("ts") or 0.0)
        hit_val = _maint_cache.get("value")
        if hit_val is not None and (now - hit_ts) < _MAINT_CACHE_TTL:
            return bool(hit_val)
    val = _read_maintenance_mode_uncached()
    with _maint_lock:
        _maint_cache["ts"] = time.monotonic()
        _maint_cache["value"] = bool(val)
    return val


def set_maintenance_mode(enabled: bool):
    val = bool(enabled)
    # Try DB first (if available), but always keep local fallback in sync.
    try:
        from bot.services.supabase_db import has_db, db_set_maintenance_mode
        if has_db():
            db_set_maintenance_mode(val)
    except Exception as e:
        logger.debug(f"Supabase set_maintenance_mode fallback: {e}")

    data = _load_settings()
    data["maintenance_mode"] = val
    _save_settings(data)
    invalidate_maintenance_mode_cache()
