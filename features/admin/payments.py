"""Admin payment approve/reject notifications."""
from __future__ import annotations

import logging

from aiogram import Bot

from database.repositories import payments as payments_repo
from database.repositories import users as users_repo
from shared.keyboards import open_services_inline
from shared.marketing import payment_approved_message, payment_rejected_message
from shared.payment_notifications import format_document_type

logger = logging.getLogger(__name__)


def _unlocked_documents(payment: dict) -> list[str]:
    doc = format_document_type(None, payment)
    key = str(payment.get("document_type") or "manual").strip().lower()
    if key == "cv":
        return ["CV"]
    if key in ("obyektivka", "oby"):
        return ["Obyektivka"]
    if key == "manual":
        return ["CV", "Obyektivka"]
    return [doc] if doc and doc != "—" else ["Hujjat"]


async def notify_payment_approved(bot: Bot, payment: dict) -> None:
    tid = int(payment.get("telegram_id") or 0)
    if not tid:
        return
    docs = _unlocked_documents(payment)
    try:
        await bot.send_message(
            tid,
            payment_approved_message(docs),
            reply_markup=open_services_inline(tid),
        )
    except Exception as exc:
        logger.warning("User approve notify failed: %s", exc)


async def notify_payment_rejected(
    bot: Bot,
    payment: dict,
    *,
    reason: str = "",
) -> None:
    tid = int(payment.get("telegram_id") or 0)
    if not tid:
        return
    doc = format_document_type(None, payment)
    try:
        await bot.send_message(
            tid,
            payment_rejected_message(doc, reason=reason),
        )
    except Exception as exc:
        logger.warning("User reject notify failed: %s", exc)


def admin_approve_summary(payment: dict) -> str:
    pid = int(payment["id"])
    docs = ", ".join(_unlocked_documents(payment))
    return f"✅ To'lov #{pid} tasdiqlandi.\n📄 Ochilgan hujjat: <b>{docs}</b>"


def admin_reject_summary(payment: dict, *, reason: str = "") -> str:
    pid = int(payment["id"])
    text = f"❌ To'lov #{pid} rad etildi."
    if reason.strip():
        text += f"\nSabab: {reason.strip()}"
    return text
