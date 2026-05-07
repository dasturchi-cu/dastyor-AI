"""Centralized keyboard builders for consistent bot UX."""
from __future__ import annotations

from telegram import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)


BTN_CV = "📄 CV Resume"
BTN_OBY = "✍️ Obyektivka"
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
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Xizmatni tanlang...",
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
