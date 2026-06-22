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
        "👋 <b>DASTYOR AI</b> — ishga kirish hujjatlaringiz tayyor!\n\n"
        "🎯 <b>3 qadamda tayyor:</b>\n"
        "1️⃣ Ovoz yoki matn yuboring\n"
        "2️⃣ AI formani to'ldiradi\n"
        "3️⃣ Demo yuklash — bepul (watermark)\n"
        "4️⃣ Tayyor fayl — to'lov kerak\n\n"
        "📄 <b>CV Resume</b> — zamonaviy PDF (ish beruvchilar uchun)\n"
        "✍️ <b>Obyektivka</b> — rasmiy Word (.docx)\n\n"
        f"💰 <b>Tayyor fayl:</b> {p} so'm (1 ta hujjat)\n"
        "🎙 Ovoz va matn to'ldirish — <b>bepul</b>\n\n"
        "👇 Qaysi hujjat kerak?"
    )


def cv_intro_header() -> str:
    return (
        "🔥 <b>Ishga kirish uchun professional CV</b> — 3 daqiqada!\n\n"
        "📄 <b>CV Resume</b>\n\n"
        "• Forma orqali to'ldiring, ovoz yoki matn yuboring\n"
        "• AI ma'lumotlarni ajratadi va formani to'ldiradi\n"
        "• Shablon: Modern / Classic / Corporate\n"
        "• Natija: <b>PDF</b> (ATS-friendly)"
    )


def oby_intro_hook() -> str:
    return (
        "🎙 <b>Ovoz va matn — bepul.</b> Tayyor Word fayl uchun to'lov kerak.\n\n"
    )


def cross_sell_cv_line() -> str:
    return "\n\n💡 <b>CV ham kerakmi?</b> Bosh menyudan 📄 CV Resume tugmasini bosing."


def cross_sell_oby_line() -> str:
    return "\n\n💡 <b>Obyektivka ham kerakmi?</b> Bosh menyudan ✍️ Obyektivka tugmasini bosing."


def payment_approved_message(credits: int) -> str:
    p = format_price_uzs()
    return (
        "✅ <b>To'lovingiz tasdiqlandi!</b>\n\n"
        f"💳 Oldin to'langan: <b>{credits}</b> ta tayyor hujjat\n"
        f"ℹ️ Yangi tayyor fayl: <b>{p} so'm</b> (CV yoki Obyektivka).\n\n"
        "👇 Hujjatni tanlang va yaratishni boshlang:"
    )
