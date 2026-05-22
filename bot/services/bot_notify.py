"""Foydalanuvchiga bot orqali xabarlar (to‘lov, hujjat)."""
from __future__ import annotations

import logging

from telegram import Bot
from telegram.error import TelegramError

from bot.ui.keyboards import service_open_inline

logger = logging.getLogger(__name__)

_STATUS_UZ = {
    "pending": "⏳ To‘lov kutilmoqda",
    "pending_payment": "⏳ To‘lov kutilmoqda",
    "payment_submitted": "⏳ Admin tekshirmoqda",
    "approved": "✅ Tasdiqlangan — formada yuklang",
    "delivered": "✅ Tasdiqlangan — formada yuklang",
    "rejected": "❌ Rad etilgan",
    "completed": "📦 Botga yuborilgan",
    "cancelled": "🚫 Bekor qilingan",
}


async def notify_payment_approved(
    bot: Bot,
    user_id: int,
    *,
    kind: str,
    request_id: int | None,
    webapp_base: str,
) -> None:
    k = (kind or "cv").strip().lower()
    svc = "cv" if k == "cv" else "obyektivka"
    label = "CV (PDF)" if svc == "cv" else "Obyektivka (Word)"
    text = (
        f"✅ <b>To‘lov OK</b> — {label}\n\n"
        f"Formani oching → <b>Botga yuborish</b>."
    )
    markup = service_open_inline(webapp_base, int(user_id), svc)
    try:
        await bot.send_message(
            chat_id=int(user_id),
            text=text,
            parse_mode="HTML",
            reply_markup=markup,
        )
    except TelegramError as e:
        logger.warning("notify_payment_approved uid=%s: %s", user_id, e)


async def notify_payment_rejected(
    bot: Bot,
    user_id: int,
    *,
    kind: str,
    request_id: int | None,
) -> None:
    k = (kind or "cv").strip().lower()
    label = "CV" if k == "cv" else "Obyektivka"
    text = (
        f"❌ <b>To‘lov rad</b> — {label}\n"
        "Qayta skrinshot yoki 🆘 Murojaat."
    )
    try:
        await bot.send_message(chat_id=int(user_id), text=text, parse_mode="HTML")
    except TelegramError as e:
        logger.warning("notify_payment_rejected uid=%s: %s", user_id, e)


async def notify_doc_delivered(bot: Bot, user_id: int, *, kind: str) -> None:
    k = (kind or "cv").strip().lower()
    label = "CV PDF" if k == "cv" else "Obyektivka Word"
    text = (
        f"📬 <b>{label}</b> yuqoridagi xabarda yuborildi.\n\n"
        "Yana kerak bo‘lsa — yangi forma va yangi to‘lov (5 000 so‘m).\n"
        "Holat: /docs"
    )
    try:
        await bot.send_message(chat_id=int(user_id), text=text, parse_mode="HTML")
    except TelegramError as e:
        logger.debug("notify_doc_delivered uid=%s: %s", user_id, e)


def paid_doc_status_label(status: str) -> str:
    try:
        from bot.services.supabase_db import normalize_paid_doc_status

        st = normalize_paid_doc_status(status or "pending")
    except Exception:
        st = (status or "pending").strip().lower()
    return _STATUS_UZ.get(st, "⏳ To‘lov kutilmoqda")
