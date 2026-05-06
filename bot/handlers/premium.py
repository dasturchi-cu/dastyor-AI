"""Minimal payment review callbacks for admin-only flow."""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.services.admin_service import is_admin
from bot.services.supabase_db import db_get_payment, db_set_payment_status

logger = logging.getLogger(__name__)


async def premium_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("Bu bo'lim o'chirilgan. Faqat CV/Obyektivka va murojaat mavjud.")


async def premium_purchase_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer("Bu funksya o'chirilgan.", show_alert=False)


async def handle_premium_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    return False


async def premium_payment_review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()
    if not query.from_user or not is_admin(query.from_user.id):
        await query.answer("Faqat admin uchun.", show_alert=True)
        return

    data = str(query.data or "")
    # Expected: prempay_approve_123 / prempay_reject_123
    parts = data.split("_")
    if len(parts) != 3:
        await query.answer("Noto'g'ri callback.", show_alert=True)
        return

    action = parts[1].strip().lower()
    try:
        payment_id = int(parts[2])
    except Exception:
        await query.answer("Payment ID xato.", show_alert=True)
        return

    payment = db_get_payment(payment_id)
    if not payment:
        await query.answer("To'lov topilmadi.", show_alert=True)
        return

    new_status = "approved" if action == "approve" else "rejected"
    ok = db_set_payment_status(payment_id, new_status)
    if not ok:
        await query.answer("Status yangilanmadi.", show_alert=True)
        return

    uid = payment.get("user_id")
    plan = payment.get("plan_type") or "service"
    msg = (
        "✅ To'lov tasdiqlandi." if new_status == "approved" else "❌ To'lov rad etildi."
    )

    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    try:
        await query.message.reply_text(
            f"{msg}\n\nPayment: #{payment_id}\nUser: {uid}\nXizmat: {plan}"
        )
    except Exception:
        logger.debug("Failed to send review result message", exc_info=True)
