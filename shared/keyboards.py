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

ADMIN_BTN_USERS = "👥 Foydalanuvchilar"
ADMIN_BTN_PAYMENTS = "💳 To'lovlar"
ADMIN_BTN_FILES = "📁 Fayllar"
ADMIN_BTN_CLOSE = "🚪 Yopish"


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
            [KeyboardButton(text=ADMIN_BTN_USERS), KeyboardButton(text=ADMIN_BTN_PAYMENTS)],
            [KeyboardButton(text=ADMIN_BTN_FILES), KeyboardButton(text=ADMIN_BTN_CLOSE)],
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
