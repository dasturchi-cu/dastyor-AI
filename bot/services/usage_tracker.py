"""
Usage Tracker Service
Tracks daily usage per user for free tier limits.
Stores data in a simple JSON file (can be migrated to DB later).
"""
import os
import json
import logging
from datetime import date
from typing import TYPE_CHECKING

from config import DAILY_FREE_LIMIT

if TYPE_CHECKING:
    from telegram import Update

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
    try:
        from bot.services.supabase_db import has_db, db_get_usage
        if has_db():
            return db_get_usage(user_id)
    except Exception as e:
        logger.debug(f"Supabase get_user_usage fallback: {e}")
    data = _load_usage()
    uid = str(user_id)
    today = get_today()
    if uid in data and data[uid].get("date") == today:
        return data[uid].get("count", 0)
    return 0

def increment_usage(user_id: int, action: str = "service") -> int:
    """Increment usage and return new count"""
    try:
        from bot.services.supabase_db import has_db, db_increment_usage, db_get_usage, db_log_usage
        if has_db():
            db_increment_usage(user_id)
            db_log_usage(user_id, action)
            return db_get_usage(user_id)
    except Exception as e:
        logger.debug(f"Supabase increment_usage fallback: {e}")
    data = _load_usage()
    uid = str(user_id)
    today = get_today()
    if uid not in data or data[uid].get("date") != today:
        data[uid] = {"date": today, "count": 0}
    data[uid]["count"] += 1
    _save_usage(data)
    return data[uid]["count"]

def get_effective_daily_cap() -> int:
    """
    Bepul tarif uchun kunlik limit.
    0 yoki manfiy = cheksiz (bepul ham).
    """
    try:
        from bot.services.settings_service import get_daily_limit

        lim = int(get_daily_limit())
        if lim <= 0:
            return 0
        return lim
    except Exception:
        pass
    return max(0, int(DAILY_FREE_LIMIT))


def has_paid_active_plan(user_id: int) -> bool:
    """Standard yoki Premium — kunlik bepul limit qo'llanmaydi."""
    try:
        from bot.services.settings_service import is_premium

        return bool(is_premium(int(user_id)))
    except Exception:
        return False


def can_use(user_id: int) -> bool:
    """Bepul foydalanuvchi: kunlik limit ichida; to'lovli: har doim True."""
    cap = get_effective_daily_cap()
    if cap <= 0:
        return True
    if has_paid_active_plan(user_id):
        return True
    return get_user_usage(user_id) < cap


def get_remaining(user_id: int) -> int:
    """Bugun qolgan bepul urinishlar (to'lovli: katta son)."""
    cap = get_effective_daily_cap()
    if cap <= 0 or has_paid_active_plan(user_id):
        return 999
    used = get_user_usage(user_id)
    return max(0, cap - used)


def get_tariff_snapshot(user_id: int) -> dict:
    """
    Bot va /api/me uchun: tarif kodi, o'zbekcha nom, kunlik limit va qoldiq.
    JSON/API uchun dict (None = cheksiz tarifda shu maydonlar yo'q).
    """
    from bot.services.settings_service import (
        get_active_plan_code,
        get_active_subscription_expires_display,
    )

    uid = int(user_id)
    plan = get_active_plan_code(uid)
    labels = {
        "free": "Oddiy (bepul)",
        "standard": "Standard",
        "premium": "Premium",
    }
    cap = get_effective_daily_cap()
    paid = has_paid_active_plan(uid)
    unlimited = cap <= 0 or paid
    used = get_user_usage(uid)
    rem = get_remaining(uid)
    return {
        "plan": plan,
        "plan_label": labels.get(plan, plan),
        "unlimited": bool(unlimited),
        "daily_limit": None if unlimited else cap,
        "used_today": None if unlimited else used,
        "remaining": None if unlimited else rem,
        "subscription_ends": (
            get_active_subscription_expires_display(uid)
            if plan in ("standard", "premium")
            else None
        ),
    }


def format_tariff_status_html(user_id: int) -> str:
    """Telegram HTML (/start, /menu)."""
    s = get_tariff_snapshot(user_id)
    if s["unlimited"]:
        lines = [f"📦 <b>Tarif:</b> {s['plan_label']} — <b>cheksiz</b>"]
        if s.get("subscription_ends"):
            lines.append(f"📅 <b>Obuna tugashi:</b> {s['subscription_ends']}")
        return "\n".join(lines)
    dl = int(s["daily_limit"] or 0)
    ut = int(s["used_today"] or 0)
    rm = 0 if s["remaining"] is None else int(s["remaining"])
    return (
        f"📦 <b>Tarif:</b> {s['plan_label']}\n"
        f"📊 <b>Bugun:</b> {ut}/{dl} · <b>Qoldi:</b> {rm}"
    )


def format_tariff_status_markdown(user_id: int) -> str:
    """Markdown (Balans va boshqa * matnlar)."""
    s = get_tariff_snapshot(user_id)
    if s["unlimited"]:
        lines = [f"📦 *Tarif:* {s['plan_label']} — *cheksiz*"]
        if s.get("subscription_ends"):
            lines.append(f"📅 *Obuna tugashi:* `{s['subscription_ends']}`")
        return "\n".join(lines)
    dl = int(s["daily_limit"] or 0)
    ut = int(s["used_today"] or 0)
    rm = 0 if s["remaining"] is None else int(s["remaining"])
    return (
        f"📦 *Tarif:* {s['plan_label']}\n"
        f"📊 *Bugun:* {ut}/{dl} · *qoldi:* {rm}"
    )


async def _send_quota_blocked_message(bot, chat_id: int, user_id: int, lang: str = "uz_lat") -> None:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
    from config import WEBAPP_BASE

    uid = int(user_id)
    cap = get_effective_daily_cap()
    used = get_user_usage(uid)
    text = (
        "⛔️ <b>Kunlik limit tugadi.</b>\n\n"
        f"Bugun: <b>{used}</b> / <b>{cap}</b> ta bepul urinish ishlatildi.\n\n"
        "💎 <b>Standard</b> yoki <b>Premium</b> obuna oling — cheksiz foydalanish.\n\n"
        "👇 Quyidagi tugma orqali tariflarni oching:"
    )
    url = f"{WEBAPP_BASE.rstrip('/')}/premium.html?telegram_id={uid}&lang={lang}"
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("💎 Tariflar (Premium/Standard)", web_app=WebAppInfo(url=url))]]
    )
    await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=kb)


async def ensure_can_use_or_notify(bot, chat_id: int, user_id: int, lang: str = "uz_lat") -> bool:
    """
    True — xizmatni boshlash mumkin.
    False — limit tugagan, foydalanuvchiga xabar yuborildi.
    """
    from bot.services.admin_service import is_admin

    uid = int(user_id)
    if is_admin(uid):
        return True
    if can_use(uid):
        return True
    await _send_quota_blocked_message(bot, chat_id, uid, lang)
    return False


async def reply_if_daily_quota_blocked(update: "Update", user_id: int, lang: str = "uz_lat") -> bool:
    """
    Limit tugagan bo'lsa xabar yuboradi va True qaytaradi (handler return qilishi kerak).
    Admin cheksiz.
    """
    uid = int(user_id)
    bot = update.get_bot()
    cid = update.effective_chat.id if update.effective_chat else uid
    if await ensure_can_use_or_notify(bot, cid, uid, lang):
        return False
    return True
