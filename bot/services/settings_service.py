"""
Settings Service (Enhanced)
Manages dynamic bot settings including detailed Premium User management.
"""
import json
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

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

# === CONFIG ===
def get_daily_limit():
    return _load_settings().get("daily_limit", 10)

def set_daily_limit(limit):
    data = _load_settings()
    data["daily_limit"] = int(limit)
    _save_settings(data)
