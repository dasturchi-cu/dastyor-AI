"""
Usage Tracker Service
Tracks daily usage per user for free tier limits.
Stores data in a simple JSON file (can be migrated to DB later).
"""
import json
import logging
import os
import threading
import time
from datetime import date
from typing import TYPE_CHECKING

from config import DAILY_FREE_LIMIT

if TYPE_CHECKING:
    from telegram import Update

logger = logging.getLogger(__name__)

USAGE_FILE = "usage_data.json"

# Tarif jadvali (bir necha Supabase so'rovini birlashtiradi) — /start va balans tezligi.
# Qisqa TTL — xizmatdan keyin Balans tez yangilansin (30s eski ko‘rinish qoldirardi)
# /start va menyu: bir necha Supabase chaqiruvini birlashtiradi — qisqa TTL sekinlik berardi.
_TARIFF_SNAPSHOT_TTL = float(os.getenv("TARIFF_SNAPSHOT_CACHE_TTL_SECONDS", "45") or "45")
_tariff_snapshot_cache: dict[int, tuple[float, dict]] = {}
_tariff_cache_lock = threading.Lock()


def invalidate_tariff_snapshot_cache(user_id: int | None = None) -> None:
    """Limit/obuna o'zgaganda (record_service_completion) chaqiriladi."""
    with _tariff_cache_lock:
        if user_id is None:
            _tariff_snapshot_cache.clear()
        else:
            _tariff_snapshot_cache.pop(int(user_id), None)

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


def _build_tariff_snapshot_uncached(user_id: int) -> dict:
    from bot.services.plan_limits import user_limits_breakdown
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
    breakdown = user_limits_breakdown(uid, plan=plan)
    subs = (
        get_active_subscription_expires_display(uid)
        if plan in ("standard", "premium")
        else None
    )
    return {
        "plan": plan,
        "plan_label": labels.get(plan, plan),
        "subscription_ends": subs,
        "limits_breakdown": breakdown,
        "unlimited": all(
            bool(b.get("unlimited")) or bool(b.get("blocked")) for b in breakdown
        ),
        "daily_limit": None,
        "used_today": None,
        "remaining": None,
    }


def get_tariff_snapshot(user_id: int) -> dict:
    """
    Bot va /api/me: tarif + har xizmat bo'yicha limit / ishlatilgan / qoldi.
    Qisqa TTL kesh — ketma-ket Supabase chaqiruvlarini kamaytiradi.
    """
    uid = int(user_id)
    now = time.monotonic()
    with _tariff_cache_lock:
        hit = _tariff_snapshot_cache.get(uid)
        if hit and (now - hit[0]) < _TARIFF_SNAPSHOT_TTL:
            return hit[1]
    snap = _build_tariff_snapshot_uncached(uid)
    with _tariff_cache_lock:
        _tariff_snapshot_cache[uid] = (time.monotonic(), snap)
    return snap


def _snapshot_has_exhausted(snapshot: dict) -> bool:
    for b in snapshot.get("limits_breakdown") or []:
        if b.get("exhausted"):
            return True
    return False


def format_tariff_status_html(user_id: int, snapshot: dict | None = None) -> str:
    """Telegram HTML (/start, /menu)."""
    s = snapshot if snapshot is not None else get_tariff_snapshot(user_id)
    lines = [
        f"📦 <b>Tarif:</b> {s['plan_label']}",
        "📋 Har xizmat alohida: <b>necha marta berilgan</b> / <b>limit</b> / <b>qancha qoldi</b> yoki <b>cheksiz</b>.",
        "👉 To'liq jadval: <b>Balans 💰</b> tugmasi.",
    ]
    if s.get("subscription_ends"):
        lines.insert(2, f"📅 <b>Obuna tugashi:</b> {s['subscription_ends']}")
    if _snapshot_has_exhausted(s):
        lines.append(
            "⚠️ <b>Ba'zi xizmatlar:</b> limit tugadi — quyidagi jadvalda qator oxirida ko'rsatilgan."
        )
        lines.append(
            "💡 <b>Yangilash:</b> mini-appda <b>💎 Premium / tariflar</b> — tarifni yangilasangiz yoki muddatni uzaytirsangiz, "
            "limitlar yangi davr bo'yicha <b>qayta hisoblanadi</b>."
        )
    return "\n".join(lines)


def format_tariff_status_markdown(user_id: int, snapshot: dict | None = None) -> str:
    """Markdown (Balans va boshqa * matnlar)."""
    s = snapshot if snapshot is not None else get_tariff_snapshot(user_id)
    lines = [
        f"📦 *Tarif:* {s['plan_label']}",
        "📋 Har xizmat: *berilgan / limit / qoldi* yoki *cheksiz* — quyida.",
    ]
    if s.get("subscription_ends"):
        lines.append(f"📅 *Obuna tugashi:* `{s['subscription_ends']}`")
    if _snapshot_has_exhausted(s):
        lines.append(
            "⚠️ *Ba'zi xizmatlar:* limit tugadi — quyidagi jadvalda qator oxirida ko'rsatilgan."
        )
        lines.append(
            "💡 *Yangilash:* mini-appda *💎 Premium / tariflar* — tarifni yangilasangiz yoki muddatni uzaytirsangiz, "
            "limitlar yangi davr bo'yicha *qayta hisoblanadi*."
        )
    return "\n".join(lines)


async def _send_quota_blocked_message(
    bot,
    chat_id: int,
    user_id: int,
    lang: str = "uz_lat",
    category: str | None = None,
) -> None:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
    from config import WEBAPP_BASE
    from bot.services.plan_limits import block_reason_for_user_uz
    from bot.services.pricing import (
        STANDARD_PRICE_UZS,
        PREMIUM_PRICE_UZS,
        REFERRAL_PREMIUM_DISCOUNT_PERCENT,
        REFERRAL_REQUIRED_INVITES,
        apply_percent_discount,
        format_uzs,
        promo_deadline_display,
        PROMO_LABEL,
    )

    uid = int(user_id)
    reason = (
        block_reason_for_user_uz(uid, category)
        if category
        else "⛔️ Bu xizmat pullik. Standard yoki Premium tarifni oling."
    )
    dl = promo_deadline_display()
    promo_line = (
        f"🔥 <b>{PROMO_LABEL}:</b> faqat shu hafta {format_uzs(STANDARD_PRICE_UZS)} / {format_uzs(PREMIUM_PRICE_UZS)} so'm."
        + (f" (deadline: {dl})" if dl else "")
    )

    # Referral pitch (we keep it simple; DB decides actual eligibility)
    disc_price = apply_percent_discount(PREMIUM_PRICE_UZS, REFERRAL_PREMIUM_DISCOUNT_PERCENT)
    ref_line = (
        f"🎁 <b>Referal bonus:</b> {REFERRAL_REQUIRED_INVITES} ta do'st taklif qilsangiz — "
        f"Premiumga <b>{REFERRAL_PREMIUM_DISCOUNT_PERCENT}%</b> chegirma "
        f"({format_uzs(disc_price)} so'm)."
    )

    text = (
        f"{reason}\n\n"
        "💡 <b>Taklif:</b>\n"
        f"- Standard: <b>{format_uzs(STANDARD_PRICE_UZS)} so'm</b> / 7 kun — Tarjima + PDF + Translit cheksiz\n"
        f"- Premium: <b>{format_uzs(PREMIUM_PRICE_UZS)} so'm</b> / 30 kun — hammasi cheksiz + Obyektivka/CV oyiga 6 ta\n"
        "⏱ 1 obyektivka ≈ 30–60 daqiqa vaqt tejaydi.\n\n"
        f"{promo_line}\n"
        f"{ref_line}\n\n"
        "👇 Tanlang:"
    )

    base = WEBAPP_BASE.rstrip("/")
    url_std = f"{base}/premium.html?telegram_id={uid}&lang={lang}&buy=standard"
    url_pre = f"{base}/premium.html?telegram_id={uid}&lang={lang}&buy=premium"
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"✅ Standard ({format_uzs(STANDARD_PRICE_UZS)})", web_app=WebAppInfo(url=url_std)),
            InlineKeyboardButton(f"⭐ Premium ({format_uzs(PREMIUM_PRICE_UZS)})", web_app=WebAppInfo(url=url_pre)),
        ]
    ])
    await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=kb)


async def ensure_can_use_or_notify(
    bot,
    chat_id: int,
    user_id: int,
    *,
    category: str,
    lang: str = "uz_lat",
) -> bool:
    """
    True — xizmatni boshlash mumkin.
    False — limit yo'q / tarifda yo'q, xabar yuborildi.
    """
    from bot.services.admin_service import is_admin
    from bot.services.plan_limits import can_use_category

    uid = int(user_id)
    if is_admin(uid):
        return True
    if can_use_category(uid, category):
        return True
    await _send_quota_blocked_message(bot, chat_id, uid, lang, category)
    return False


async def reply_if_daily_quota_blocked(
    update: "Update",
    user_id: int,
    *,
    category: str,
    lang: str = "uz_lat",
) -> bool:
    """
    Limit tugagan bo'lsa xabar yuboradi va True qaytaradi (handler return qilishi kerak).
    Admin cheksiz.
    """
    uid = int(user_id)
    bot = update.get_bot()
    cid = update.effective_chat.id if update.effective_chat else uid
    if await ensure_can_use_or_notify(bot, cid, uid, category=category, lang=lang):
        return False
    return True
