"""Centralized keyboard builders for consistent bot UX."""
from __future__ import annotations

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from bot.utils.i18n import _DICT
from config import WEBAPP_VERSION

# Reply keyboard — WebApp yo‘q (bosilganda avval tushuntirish chiqadi)
BTN_CV = "📄 CV Resume"
BTN_OBY = "✍️ Obyektivka"
BTN_CONTACT = "🆘 Murojaat"
BTN_HELP = "ℹ️ Yordam"
BTN_BACK = "🔙 Orqaga"

ADMIN_BTN_STATS = "📊 Holat"
ADMIN_BTN_SUPPORT = "📨 Murojaatlar"
ADMIN_BTN_PAYMENTS = "💳 To'lovlar"
ADMIN_BTN_CLOSE = "🚪 Yopish"


def _labels_from_i18n(key: str) -> set[str]:
    block = _DICT.get(key) or {}
    return {str(v).strip() for v in block.values() if v}


def cv_button_labels() -> frozenset[str]:
    return frozenset({BTN_CV, *_labels_from_i18n("btn_cv")})


def oby_button_labels() -> frozenset[str]:
    return frozenset({BTN_OBY, *_labels_from_i18n("btn_oby")})


def user_reply_menu(webapp_base: str, uid: int) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(BTN_CV), KeyboardButton(BTN_OBY)],
            [KeyboardButton(BTN_CONTACT), KeyboardButton(BTN_HELP)],
            [KeyboardButton(BTN_BACK)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Xizmatni tanlang...",
    )


def service_open_inline(webapp_base: str, uid: int, service: str) -> InlineKeyboardMarkup:
    """Forma ochish — faqat tushuntirishdan keyin."""
    base = (webapp_base or "").rstrip("/")
    ver = WEBAPP_VERSION
    if service == "cv":
        url = f"{base}/cv.html?telegram_id={uid}&v={ver}"
        label = "🚀 CV formasini ochish"
    else:
        url = f"{base}/obyektivka.html?telegram_id={uid}&v={ver}"
        label = "🚀 Obyektivka formasini ochish"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(label, web_app=WebAppInfo(url=url))],
            [InlineKeyboardButton("🔙 Boshqa xizmatlar", callback_data="menu_back")],
        ]
    )


def user_inline_start_menu(webapp_base: str, uid: int) -> InlineKeyboardMarkup:
    """/start — qisqa tanlov (forma ochish emas, faqat yo‘riqnoma tugmalari)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(BTN_CV, callback_data="intro_cv"),
                InlineKeyboardButton(BTN_OBY, callback_data="intro_oby"),
            ],
            [
                InlineKeyboardButton(BTN_CONTACT, callback_data="intro_contact"),
                InlineKeyboardButton(BTN_HELP, callback_data="intro_help"),
            ],
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
