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
BTN_REFERRAL = "🎁 Do'stni taklif qilish"

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
        BTN_REFERRAL,
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
ADMIN_BTN_CHANNELS = "📢 Majburiy kanallar"
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
        ADMIN_BTN_CHANNELS,
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
    """Asosiy menyu — eng ko'p ishlatiladigan 5 ta amal.

    Muqova xati / Tarjima / Namunalar — /cover, /translate buyruqlari va
    Yordam ekranidagi tezkor tugmalar orqali hamon bir bosishda ochiladi.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CV), KeyboardButton(text=BTN_OBY)],
            [KeyboardButton(text=BTN_CREDITS), KeyboardButton(text=BTN_REFERRAL)],
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
    """To'lovdan keyin — 1-click hujjat yuklash + cross-sell."""
    from shared.payment_notifications import normalize_payment_service, payment_service_command

    service = normalize_payment_service(document_type)
    cmd = payment_service_command(document_type)
    rows: list[list[InlineKeyboardButton]] = []

    if service == "cover":
        rows.append(
            [InlineKeyboardButton(text="📥 Muqova xatini hozir yaratish", callback_data="postpay_cover")]
        )
    elif service == "translate":
        rows.append(
            [InlineKeyboardButton(text="🌐 Tarjimani hozir boshlash", callback_data="postpay_translate")]
        )
    else:
        page = "cv.html" if service == "cv" else "obyektivka.html"
        url = webapp_url(uid, page)
        if url:
            # ready_export=1 → WebApp ochilganda toza faylni 1 bosishda yuboradi
            url = f"{url}&voice=1&autoload=1&ready_export=1"
        if url:
            label = (
                "📥 CV ni hozir yuklash"
                if service == "cv"
                else "📥 Obyektivkani hozir yuklash"
            )
            rows.append([InlineKeyboardButton(text=label, web_app=WebAppInfo(url=url))])

    if service in ("cv", "obyektivka"):
        other_page = "obyektivka.html" if service == "cv" else "cv.html"
        other_url = webapp_url(uid, other_page)
        if other_url:
            other_url = f"{other_url}&voice=1&autoload=1&ready_export=1"
            other_label = (
                "✍️ Obyektivka ham yaratish"
                if service == "cv"
                else "📄 CV ham yaratish"
            )
            rows.append([InlineKeyboardButton(text=other_label, web_app=WebAppInfo(url=other_url))])
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
    return package_choice_keyboard(uid)


def package_choice_keyboard(uid: int, document_type: str | None = None) -> InlineKeyboardMarkup:
    from shared.pricing import format_uzs, list_packages

    rows: list[list[InlineKeyboardButton]] = []
    for p in list_packages():
        badge = f" · {p['badge']}" if p.get("badge") else ""
        text = f"{p['credits']}× — {format_uzs(p['price_uzs'])} so'm{badge}"
        rows.append(
            [
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"pay_pack_{p['id']}",
                )
            ]
        )
    web_url = _web_pay_url(uid, document_type)
    if web_url:
        rows.append(
            [InlineKeyboardButton(text="💳 Web-ilova orqali to'lash", web_app=WebAppInfo(url=web_url))]
        )
    # Referral share — to'lov klaviaturasini chalkashtirmaslik uchun bu yerda yo'q
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payment_rejected_keyboard(uid: int, document_type: str | None = None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="🔄 Paket tanlash", callback_data="pay_via_bot")],
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


def referral_link(uid: int) -> str:
    bot_username = (settings.bot_username or "DastyorAiBot").lstrip("@")
    return f"https://t.me/{bot_username}?start=ref_{int(uid)}"


def referral_share_button(uid: int) -> InlineKeyboardButton:
    """Telegram share — 1 do'st to'lasa = +1."""
    from urllib.parse import quote

    ref = referral_link(uid)
    share_text = f"DASTYOR AI — CV/obyektivka 1 daqiqada.\n{ref}"
    share_url = (
        "https://t.me/share/url?url="
        + quote(ref, safe="")
        + "&text="
        + quote(share_text, safe="")
    )
    return InlineKeyboardButton(text="📤 Do'stga ulashish (+1)", url=share_url)


def referral_share_keyboard(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[referral_share_button(uid)]])


def document_ready_share_note() -> str:
    return ""


def payment_choice_keyboard(uid: int, document_type: str | None = None) -> InlineKeyboardMarkup:
    """Balans / paywall — paket tanlash."""
    return package_choice_keyboard(uid, document_type)


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


def help_quick_actions_kb() -> InlineKeyboardMarkup:
    """Yordam ekranidagi tezkor tugmalar — asosiy menyudan olib tashlangan xizmatlar."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_COVER, callback_data="postpay_cover")],
            [InlineKeyboardButton(text=BTN_TRANSLATE, callback_data="postpay_translate")],
            [InlineKeyboardButton(text=BTN_SAMPLES, callback_data="help_samples")],
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
            [KeyboardButton(text=ADMIN_BTN_CHANNELS), KeyboardButton(text=ADMIN_BTN_SECURITY)],
            [KeyboardButton(text=ADMIN_BTN_DASHBOARD), KeyboardButton(text=ADMIN_BTN_ERRORS)],
            [KeyboardButton(text=ADMIN_BTN_CLOSE)],
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


