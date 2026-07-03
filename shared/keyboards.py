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
BTN_COVER = "📝 Muqova xati"
BTN_TRANSLATE = "🌐 Tarjima"
BTN_BACK = "🔙 Orqaga"
BTN_HELP = "ℹ️ Yordam"
BTN_CREDITS = "💳 Pul balansi"
BTN_SAMPLES = "📁 Namunalar"

# Eski Telegram klaviatura (cache) — menyu tugmasi sifatida tanish
LEGACY_BTN_CREDITS = ("💳 Kreditlar", "Kreditlar", "💳 Kredit")

MENU_BUTTON_TEXTS = frozenset(
    {
        BTN_CV,
        BTN_OBY,
        BTN_COVER,
        BTN_TRANSLATE,
        BTN_CREDITS,
        BTN_HELP,
        BTN_SAMPLES,
        BTN_BACK,
        *LEGACY_BTN_CREDITS,
    }
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
ADMIN_BTN_SECURITY = "🔒 Xavfsizlik"
ADMIN_BTN_AI = "🤖 AI holati"
ADMIN_BTN_AI_PROBE = "🧪 AI kalit test"
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
        ADMIN_BTN_SECURITY,
        ADMIN_BTN_AI,
        ADMIN_BTN_AI_PROBE,
        ADMIN_BTN_CLOSE,
    }
)


def is_admin_menu_button(text: str | None) -> bool:
    return (text or "").strip() in ADMIN_MENU_TEXTS


def webapp_url(uid: int, page: str) -> str | None:
    base = settings.webapp_base.rstrip("/")
    if not base.startswith("https://"):
        return None
    import time
    return f"{base}/{page}?telegram_id={uid}&v={int(time.time())}"


def user_menu(uid: int | None = None) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CV), KeyboardButton(text=BTN_OBY)],
            [KeyboardButton(text=BTN_COVER), KeyboardButton(text=BTN_TRANSLATE)],
            [KeyboardButton(text=BTN_CREDITS), KeyboardButton(text=BTN_SAMPLES)],
            [KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Xizmatni tanlang",
    )


def back_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True,
    )


def contact_admin_kb(username: str) -> InlineKeyboardMarkup:
    handle = username.lstrip("@")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✉️ Adminga yozish", url=f"https://t.me/{handle}")]
        ]
    )


def open_webapp_inline(uid: int, service: str) -> InlineKeyboardMarkup:
    page = "cv.html" if service == "cv" else "obyektivka.html"
    url = webapp_url(uid, page)
    if url and service == "cv":
        url = f"{url}&autoload=1&voice=1"
    elif url and service == "obyektivka":
        url = f"{url}&autoload=1&voice=1"
    label = "🚀 CV formasini ochish / Tahrirlash" if service == "cv" else "🚀 Obyektivka formasini ochish / Tahrirlash"
    if not url:
        return InlineKeyboardMarkup(inline_keyboard=[])
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=label, web_app=WebAppInfo(url=url))]]
    )


def open_services_after_payment_inline(uid: int, document_type: str | None = None) -> InlineKeyboardMarkup:
    """To'lovdan keyin — tanlangan xizmat + cross-sell."""
    from shared.payment_notifications import normalize_payment_service, payment_service_command

    service = normalize_payment_service(document_type)
    cmd = payment_service_command(document_type)
    rows: list[list[InlineKeyboardButton]] = []

    if service == "cover":
        rows.append([InlineKeyboardButton(text=f"📝 Muqova xati ({cmd})", callback_data="postpay_cover")])
    elif service == "translate":
        rows.append(
            [InlineKeyboardButton(text=f"🌐 Hujjat tarjimasi ({cmd})", callback_data="postpay_translate")]
        )
    else:
        page = "cv.html" if service == "cv" else "obyektivka.html"
        url = webapp_url(uid, page)
        if url:
            url = f"{url}&voice=1&autoload=1"
        if url:
            label = (
                f"📄 CV yaratish ({cmd})"
                if service == "cv"
                else f"✍️ Obyektivka yaratish ({cmd})"
            )
            rows.append([InlineKeyboardButton(text=label, web_app=WebAppInfo(url=url))])

    if service in ("cv", "obyektivka"):
        rows.append([InlineKeyboardButton(text="📝 Muqova xati (/cover)", callback_data="postpay_cover")])
        rows.append(
            [InlineKeyboardButton(text="🌐 Hujjat tarjimasi (/translate)", callback_data="postpay_translate")]
        )
    elif service == "cover":
        rows.append(
            [InlineKeyboardButton(text="🌐 Hujjat tarjimasi (/translate)", callback_data="postpay_translate")]
        )
    elif service == "translate":
        rows.append([InlineKeyboardButton(text="📝 Muqova xati (/cover)", callback_data="postpay_cover")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def open_services_inline(uid: int) -> InlineKeyboardMarkup:
    """To'lovdan keyin yoki marketing — barcha xizmat tugmalari."""
    rows: list[list[InlineKeyboardButton]] = []
    cv_url = webapp_url(uid, "cv.html")
    oby_url = webapp_url(uid, "obyektivka.html")
    if cv_url:
        cv_url = f"{cv_url}&voice=1&autoload=1"
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
    rows.append(
        [InlineKeyboardButton(text="📝 Muqova xati (/cover)", callback_data="postpay_cover")]
    )
    rows.append(
        [InlineKeyboardButton(text="🌐 Hujjat tarjimasi (/translate)", callback_data="postpay_translate")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _pay_bot_type_callback(document_type: str | None) -> str:
    from shared.payment_notifications import normalize_payment_service

    service = normalize_payment_service(document_type)
    mapping = {
        "cv": "pay_bot_type_cv",
        "obyektivka": "pay_bot_type_oby",
        "cover": "pay_bot_type_cover",
        "translate": "pay_bot_type_translate",
    }
    return mapping.get(service, "pay_via_bot")


def insufficient_balance_keyboard(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Balansni to'ldirish", callback_data="pay_via_bot")],
        ]
    )


def payment_rejected_keyboard(uid: int, document_type: str | None = None) -> InlineKeyboardMarkup:
    retry_cb = _pay_bot_type_callback(document_type)
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="🔄 Qayta to'lov qilish", callback_data=retry_cb)],
    ]
    web_url = _web_pay_url(uid, document_type)
    if web_url:
        rows.append(
            [InlineKeyboardButton(text="💳 Web orqali to'lash", web_app=WebAppInfo(url=web_url))]
        )
    rows.append([InlineKeyboardButton(text="💳 Pul balansi", callback_data="pay_show_balance")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _web_pay_url(uid: int, document_type: str | None = None) -> str | None:
    from shared.payment_notifications import normalize_payment_service

    service = normalize_payment_service(document_type) if document_type else "cv"
    page = "obyektivka.html" if service == "obyektivka" else "cv.html"
    url = webapp_url(uid, page)
    if not url:
        return None
    pay_url = f"{url}&pay=1"
    if service in ("cover", "translate"):
        pay_url = f"{pay_url}&pay_service={service}"
    return pay_url


def payment_choice_keyboard(uid: int, document_type: str | None = None) -> InlineKeyboardMarkup:
    url = _web_pay_url(uid, document_type)
    keyboard: list[list[InlineKeyboardButton]] = []
    if url:
        keyboard.append(
            [InlineKeyboardButton(text="💳 Web-ilova orqali to'lash", web_app=WebAppInfo(url=url))]
        )
    keyboard.append(
        [InlineKeyboardButton(text="🤖 Telegram bot orqali to'lash", callback_data="pay_via_bot")]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def open_oby_preview_inline(uid: int, *, missing_count: int = 0) -> InlineKeyboardMarkup:
    base = settings.webapp_base.rstrip("/")
    if not base.startswith("https://"):
        return InlineKeyboardMarkup(inline_keyboard=[])
    import time
    url = (
        f"{base}/obyektivka.html?telegram_id={uid}"
        f"&v={int(time.time())}&autoload=1&voice=1"
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
            [KeyboardButton(text=ADMIN_BTN_AI), KeyboardButton(text=ADMIN_BTN_AI_PROBE)],
            [KeyboardButton(text=ADMIN_BTN_DASHBOARD), KeyboardButton(text=ADMIN_BTN_SECURITY)],
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


