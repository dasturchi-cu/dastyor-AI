"""Centralized keyboard builders for consistent bot UX."""
from __future__ import annotations

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)


BTN_CV = "📄 CV ochish"
BTN_OBY = "📝 Obyektivka ochish"
BTN_CONTACT = "🆘 Murojaat"
BTN_HELP = "ℹ️ Yordam"

ADMIN_BTN_STATS = "📊 Holat"
ADMIN_BTN_SUPPORT = "📨 Murojaatlar"
ADMIN_BTN_PAYMENTS = "💳 To'lovlar"
ADMIN_BTN_CLOSE = "🚪 Yopish"


def user_reply_menu(webapp_base: str, uid: int) -> ReplyKeyboardMarkup:
    base = (webapp_base or "").rstrip("/")
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=BTN_CV, web_app=WebAppInfo(url=f"{base}/cv.html?telegram_id={uid}")),
                KeyboardButton(text=BTN_OBY, web_app=WebAppInfo(url=f"{base}/obyektivka.html?telegram_id={uid}")),
            ],
            [KeyboardButton(BTN_CONTACT), KeyboardButton(BTN_HELP)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Xizmatni tanlang...",
    )


def user_inline_start_menu(webapp_base: str, uid: int) -> InlineKeyboardMarkup:
    base = (webapp_base or "").rstrip("/")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_CV, web_app=WebAppInfo(url=f"{base}/cv.html?telegram_id={uid}"))],
            [InlineKeyboardButton(text=BTN_OBY, web_app=WebAppInfo(url=f"{base}/obyektivka.html?telegram_id={uid}"))],
        ]
    )

def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(ADMIN_BTN_STATS), KeyboardButton(ADMIN_BTN_SUPPORT)],
            [KeyboardButton(ADMIN_BTN_PAYMENTS), KeyboardButton(ADMIN_BTN_CLOSE)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Admin bo'limi",
    )
