"""
Usage Tracker Service
Tracks daily usage per user for free tier limits.
Stores data in a simple JSON file (can be migrated to DB later).
"""
import os
import json
import logging
from datetime import datetime, date
from config import DAILY_FREE_LIMIT

logger = logging.getLogger(__name__)

USAGE_FILE = "usage_data.json"

def _load_usage() -> dict:
    """Load usage data from file"""
    if not os.path.exists(USAGE_FILE):
        return {}
    try:
        with open(USAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def _save_usage(data: dict):
    """Save usage data to file"""
    try:
        with open(USAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save usage: {e}")

def get_today() -> str:
    return date.today().isoformat()

def get_user_usage(user_id: int) -> int:
    """Get today's usage count for a user"""
    data = _load_usage()
    uid = str(user_id)
    today = get_today()
    
    if uid in data and data[uid].get("date") == today:
        return data[uid].get("count", 0)
    return 0

def increment_usage(user_id: int) -> int:
    """Increment usage and return new count"""
    data = _load_usage()
    uid = str(user_id)
    today = get_today()
    
    if uid not in data or data[uid].get("date") != today:
        data[uid] = {"date": today, "count": 0}
    
    data[uid]["count"] += 1
    _save_usage(data)
    return data[uid]["count"]

def can_use(user_id: int) -> bool:
    """Check if user can use a service (within daily limit)"""
    if DAILY_FREE_LIMIT <= 0:
        return True  # Unlimited
    return get_user_usage(user_id) < DAILY_FREE_LIMIT

def get_remaining(user_id: int) -> int:
    """Get remaining free uses for today"""
    if DAILY_FREE_LIMIT <= 0:
        return 999
    used = get_user_usage(user_id)
    return max(0, DAILY_FREE_LIMIT - used)
