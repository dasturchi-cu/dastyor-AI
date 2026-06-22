"""Aiogram 3 keyboard builders."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from config.settings import settings

BTN_CV = "📄 CV Resume"
BTN_OBY = "✍️ Obyektivka yaratish"
BTN_BACK = "🔙 Orqaga"
BTN_HELP = "ℹ️ Yordam"
BTN_CREDITS = "💳 Pul balansi"

# Eski Telegram klaviatura (cache) — menyu tugmasi sifatida tanish
LEGACY_BTN_CREDITS = ("💳 Kreditlar", "Kreditlar", "💳 Kredit")

MENU_BUTTON_TEXTS = frozenset(
    {BTN_CV, BTN_OBY, BTN_CREDITS, BTN_HELP, BTN_BACK, *LEGACY_BTN_CREDITS}
)


def is_credits_button(text: str | None) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if t == BTN_CREDITS or t in LEGACY_BTN_CREDITS:
        return True
    low = t.casefold()
    return t.startswith("💳") and ("kredit" in low or "pul balans" in low)


def is_menu_button(text: str | None) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if t in MENU_BUTTON_TEXTS:
        return True
    if t.casefold() in ("bekor",):
        return True
    if is_credits_button(t):
        return True
    return False

ADMIN_BTN_USERS = "👥 Foydalanuvchilar"
ADMIN_BTN_SEARCH = "🔍 Qidirish"
ADMIN_BTN_PAYMENTS = "💳 To'lovlar"
ADMIN_BTN_PENDING = "📥 Kutilayotgan"
ADMIN_BTN_STATS = "📊 Statistika"
ADMIN_BTN_ACTIVITY = "🔥 Faollik"
ADMIN_BTN_BROADCAST = "📢 Xabar yuborish"
ADMIN_BTN_EXPORT = "📥 Export"
ADMIN_BTN_TOP = "🏆 TOP 10"
ADMIN_BTN_ERRORS = "⚠️ Xatolar"
ADMIN_BTN_FILES = "📁 Fayllar"
ADMIN_BTN_SETTINGS = "⚙️ Sozlamalar"
ADMIN_BTN_DASHBOARD = "🔄 Dashboard"
ADMIN_BTN_CLOSE = "🚪 Yopish"

ADMIN_MENU_TEXTS = frozenset(
    {
        ADMIN_BTN_USERS,
        ADMIN_BTN_SEARCH,
        ADMIN_BTN_PAYMENTS,
        ADMIN_BTN_PENDING,
        ADMIN_BTN_STATS,
        ADMIN_BTN_ACTIVITY,
        ADMIN_BTN_BROADCAST,
        ADMIN_BTN_EXPORT,
        ADMIN_BTN_TOP,
        ADMIN_BTN_ERRORS,
        ADMIN_BTN_FILES,
        ADMIN_BTN_SETTINGS,
        ADMIN_BTN_DASHBOARD,
        ADMIN_BTN_CLOSE,
    }
)


def is_admin_menu_button(text: str | None) -> bool:
    return (text or "").strip() in ADMIN_MENU_TEXTS


def webapp_url(uid: int, page: str) -> str | None:
    base = settings.webapp_base.rstrip("/")
    if not base.startswith("https://"):
        return None
    return f"{base}/{page}?telegram_id={uid}&v={settings.webapp_version}"


def user_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CV), KeyboardButton(text=BTN_OBY)],
            [KeyboardButton(text=BTN_CREDITS), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Xizmatni tanlang",
    )


def back_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True,
    )


def open_webapp_inline(uid: int, service: str) -> InlineKeyboardMarkup:
    page = "cv.html" if service == "cv" else "obyektivka.html"
    url = webapp_url(uid, page)
    label = "🚀 CV formasini ochish" if service == "cv" else "🚀 Obyektivka formasini ochish"
    if not url:
        return InlineKeyboardMarkup(inline_keyboard=[])
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=label, web_app=WebAppInfo(url=url))]]
    )


def open_services_inline(uid: int) -> InlineKeyboardMarkup:
    """To'lovdan keyin yoki marketing — ikkala xizmat tugmasi."""
    rows: list[list[InlineKeyboardButton]] = []
    cv_url = webapp_url(uid, "cv.html")
    oby_url = webapp_url(uid, "obyektivka.html")
    if oby_url:
        oby_url = f"{oby_url}&voice=1&autoload=1"
    if cv_url:
        rows.append(
            [InlineKeyboardButton(text="📄 CV yaratish", web_app=WebAppInfo(url=cv_url))]
        )
    if oby_url:
        rows.append(
            [InlineKeyboardButton(text="✍️ Obyektivka yaratish", web_app=WebAppInfo(url=oby_url))]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def open_oby_preview_inline(uid: int, *, missing_count: int = 0) -> InlineKeyboardMarkup:
    base = settings.webapp_base.rstrip("/")
    if not base.startswith("https://"):
        return InlineKeyboardMarkup(inline_keyboard=[])
    url = (
        f"{base}/obyektivka.html?telegram_id={uid}"
        f"&v={settings.webapp_version}&autoload=1&voice=1"
    )
    if missing_count:
        url += f"&missing={missing_count}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👁 Preview va Tasdiqlash", web_app=WebAppInfo(url=url))]
        ]
    )


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=ADMIN_BTN_USERS), KeyboardButton(text=ADMIN_BTN_SEARCH)],
            [KeyboardButton(text=ADMIN_BTN_PAYMENTS), KeyboardButton(text=ADMIN_BTN_PENDING)],
            [KeyboardButton(text=ADMIN_BTN_STATS), KeyboardButton(text=ADMIN_BTN_ACTIVITY)],
            [KeyboardButton(text=ADMIN_BTN_BROADCAST), KeyboardButton(text=ADMIN_BTN_EXPORT)],
            [KeyboardButton(text=ADMIN_BTN_TOP), KeyboardButton(text=ADMIN_BTN_SETTINGS)],
            [KeyboardButton(text=ADMIN_BTN_FILES), KeyboardButton(text=ADMIN_BTN_DASHBOARD)],
            [KeyboardButton(text=ADMIN_BTN_ERRORS), KeyboardButton(text=ADMIN_BTN_CLOSE)],
        ],
        resize_keyboard=True,
    )


def payment_review_kb(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"pay_approve_{payment_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"pay_reject_{payment_id}"),
            ]
        ]
    )
