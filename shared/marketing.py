"""User-facing marketing copy (bot + notifications)."""
from __future__ import annotations

from config.settings import settings


def format_price_uzs(amount: int | None = None) -> str:
    n = int(amount if amount is not None else settings.single_doc_price_uzs)
    return f"{n:,}".replace(",", " ")


def price_tag() -> str:
    return f"{format_price_uzs()} so'm = 1 hujjat"


def welcome_message() -> str:
    p = format_price_uzs()
    return (
        "👋 <b>DASTYOR AI</b> — ishga kirish hujjatlaringizni 1 daqiqada tayyorlang!\n\n"
        "🎯 <b>3 qadamda tayyor:</b>\n"
        "1️⃣ Ovozli xabar yoki matn yuboring (yoki pastdagi tugmani bosing)\n"
        "2️⃣ AI formani avtomatik to'ldiradi\n"
        "3️⃣ Hujjatni tekshiring va yuklab oling\n\n"
        "📄 <b>CV Resume</b> — zamonaviy PDF format\n"
        "✍️ <b>Obyektivka</b> — rasmiy Word (.docx) format\n"
        "📝 <b>Muqova xati</b> — AI Cover Letter\n"
        "🌐 <b>Tarjima</b> — hujjatni ingliz yoki rus tiliga\n\n"
        "🎁 <b>Ajoyib yangilik:</b> Yangi foydalanuvchilar uchun <b>birinchi hujjatni yaratish va yuklash mutlaqo BEPUL!</b>\n"
        "🎙 Tahrirlash va tahlil qilish — <b>bepul</b>\n"
        f"💰 Keyingi hujjatlar: <b>{p} so'm</b> = 1 ta yuklash\n\n"
        "👇 Boshlash uchun xizmatlardan birini tanlang:"
    )


def cv_intro_header() -> str:
    return (
        "📄 <b>CV Resume</b> — AI yordamida 1 daqiqada!\n"
        "🎙 Ovoz yoki 📝 matn yuboring — AI avtomatik to'ldiradi."
    )


def oby_intro_hook() -> str:
    return (
        "✍️ <b>Obyektivka</b> — AI yordamida tez va oson!\n"
        "🎙 Ovoz va matn — bepul. Tayyor Word fayl uchun to'lov kerak.\n\n"
    )


def cross_sell_cv_line() -> str:
    return "\n\n💡 <b>CV ham kerakmi?</b> Bosh menyudan 📄 CV Resume tugmasini bosing."


def cross_sell_oby_line() -> str:
    return "\n\n💡 <b>Obyektivka ham kerakmi?</b> Bosh menyudan ✍️ Obyektivka tugmasini bosing."


def cross_sell_cover_line() -> str:
    return "\n\n💡 <b>Muqova xati kerakmi?</b> Bosh menyudan 📝 Muqova xati tugmasini bosing yoki /cover yozing."


def cross_sell_translate_line() -> str:
    return "\n\n💡 <b>Tarjima kerakmi?</b> Bosh menyudan 🌐 Tarjima tugmasini bosing yoki /translate yozing."


def payment_approved_message(credits: int, document_type: str | None = None) -> str:
    from shared.payment_notifications import format_document_type, payment_service_command

    p = format_price_uzs()
    service_label = format_document_type(document_type)
    service_cmd = payment_service_command(document_type)
    service_hint = f"{service_label} — <code>{service_cmd}</code>"
    return (
        "✅ <b>To'lovingiz tasdiqlandi!</b>\n\n"
        "Admin to'lovingizni ko'rib chiqdi va tasdiqladi.\n\n"
        f"💳 <b>Joriy balans:</b> {credits} ta yuklash\n"
        f"ℹ️ 1 ta yuklash = <b>{p} so'm</b> (CV, Obyektivka, Muqova xati, Tarjima — barchasiga)\n"
        f"📄 Tanlangan xizmat: {service_hint}\n\n"
        "👇 Xizmatingizni boshlang:"
    )
