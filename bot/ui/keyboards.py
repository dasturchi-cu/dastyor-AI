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
BTN_MY_DOCS = "📂 Mening hujjatlarim"
BTN_BACK = "🔙 Orqaga"

ADMIN_BTN_STATS = "📊 Holat"
ADMIN_BTN_SUPPORT = "📨 Murojaatlar"
ADMIN_BTN_PAYMENTS = "💳 To'lovlar"
ADMIN_BTN_DIGEST = "📋 Kunlik hisobot"
ADMIN_BTN_CLOSE = "🚪 Yopish"


def _labels_from_i18n(key: str) -> set[str]:
    block = _DICT.get(key) or {}
    return {str(v).strip() for v in block.values() if v}


def cv_button_labels() -> frozenset[str]:
    return frozenset({BTN_CV, *_labels_from_i18n("btn_cv")})


def oby_button_labels() -> frozenset[str]:
    return frozenset({BTN_OBY, *_labels_from_i18n("btn_oby")})


def my_docs_button_labels() -> frozenset[str]:
    return frozenset({BTN_MY_DOCS})


def contact_button_labels() -> frozenset[str]:
    return frozenset({BTN_CONTACT, *_labels_from_i18n("btn_contact")})


def help_button_labels() -> frozenset[str]:
    return frozenset({BTN_HELP, *_labels_from_i18n("btn_help")})


def user_reply_menu(webapp_base: str, uid: int) -> ReplyKeyboardMarkup:
    """Oddiy matn tugmalar — WebApp yo‘q (eski WebApp menyu ustiga yoziladi)."""
    _ = webapp_base, uid  # inline forma URL uchun alohida service_open_inline
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(BTN_CV), KeyboardButton(BTN_OBY)],
            [KeyboardButton(BTN_CONTACT), KeyboardButton(BTN_HELP)],
            [KeyboardButton(BTN_BACK)],
        ],
        resize_keyboard=True,
        is_persistent=False,
        input_field_placeholder="CV yoki Obyektivka",
    )


def _resolved_webapp_base(webapp_base: str) -> str:
    base = (webapp_base or "").strip().rstrip("/")
    if base.startswith("https://"):
        return base
    try:
        from config import resolve_webapp_base

        return resolve_webapp_base()
    except Exception:
        return ""


def webapp_service_url(webapp_base: str, uid: int, service: str) -> str | None:
    """Telegram WebApp uchun to‘liq https URL."""
    base = _resolved_webapp_base(webapp_base)
    if not base.startswith("https://"):
        return None
    ver = WEBAPP_VERSION
    page = "cv.html" if service == "cv" else "obyektivka.html"
    return f"{base}/{page}?telegram_id={uid}&v={ver}"


def service_open_inline(webapp_base: str, uid: int, service: str) -> InlineKeyboardMarkup:
    """Forma ochish — faqat tushuntirishdan keyin."""
    url = webapp_service_url(webapp_base, uid, service)
    if service == "cv":
        label = "🚀 CV formasini ochish"
    else:
        label = "🚀 Obyektivka formasini ochish"
    row_open: list[InlineKeyboardButton]
    if url:
        row_open = [InlineKeyboardButton(label, web_app=WebAppInfo(url=url))]
    else:
        row_open = [InlineKeyboardButton("🔙 Boshqa xizmatlar", callback_data="menu_back")]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            row_open,
            [InlineKeyboardButton("🔙 Boshqa xizmatlar", callback_data="menu_back")],
        ]
    )


def user_inline_start_menu(webapp_base: str, uid: int) -> InlineKeyboardMarkup:
    """Inline — CV, Obyektivka, Murojaat."""
    _ = webapp_base, uid
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(BTN_CV, callback_data="intro_cv"),
                InlineKeyboardButton(BTN_OBY, callback_data="intro_oby"),
            ],
            [InlineKeyboardButton(BTN_CONTACT, callback_data="intro_contact")],
        ]
    )


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(ADMIN_BTN_STATS), KeyboardButton(ADMIN_BTN_SUPPORT)],
            [KeyboardButton(ADMIN_BTN_PAYMENTS), KeyboardButton(ADMIN_BTN_DIGEST)],
            [KeyboardButton(ADMIN_BTN_CLOSE)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Admin bo'limi",
    )
