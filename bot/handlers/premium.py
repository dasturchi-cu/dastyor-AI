"""Minimal payment review callbacks for admin-only flow."""
from __future__ import annotations

import json
import logging
import os

from telegram import Update
from telegram.ext import ContextTypes

from bot.services.admin_service import is_admin
from bot.services.plan_limits import CAT_CV, CAT_OBYEKTIVKA
from bot.services.supabase_db import (
    db_get_payment,
    db_grant_cv_access,
    db_grant_objective_access,
    db_service_buckets_delete_many,
    db_set_paid_doc_request_status,
    db_set_payment_status,
    payment_normalize_plan_type,
)

logger = logging.getLogger(__name__)


def _paid_doc_meta_from_payment(payment: dict) -> tuple[int | None, str | None]:
    """payments.metadata yoki admin_note dan paid_doc request id + kind."""
    meta = payment.get("metadata")
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}
    if not isinstance(meta, dict):
        meta = {}
    rid = meta.get("paid_doc_request_id")
    try:
        rid_i = int(rid) if rid is not None else None
    except Exception:
        rid_i = None
    kind = (meta.get("paid_doc_kind") or "").strip().lower() or None
    if rid_i and kind in ("cv", "obyektivka"):
        return rid_i, kind
    note = (payment.get("admin_note") or "").strip()
    if note.startswith("paid_doc:"):
        parts = note.split(":", 2)
        if len(parts) >= 3:
            try:
                k = parts[2].strip().lower()
                if k in ("cv", "obyektivka"):
                    return int(parts[1]), k
            except Exception:
                pass
    return None, None


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
    plan_raw = payment.get("plan_type")
    plan = payment_normalize_plan_type(plan_raw)
    rid, pdkind = _paid_doc_meta_from_payment(payment)
    if plan not in ("cv", "objective") and pdkind:
        plan = "cv" if pdkind == "cv" else "objective"

    if new_status == "approved" and uid is not None:
        try:
            uid_i = int(uid)
            if plan == "cv":
                db_grant_cv_access(uid_i, True)
                db_service_buckets_delete_many(uid_i, [f"paid_once:{CAT_CV}:{uid_i}"])
            elif plan == "objective":
                db_grant_objective_access(uid_i, True)
                db_service_buckets_delete_many(uid_i, [f"paid_once:{CAT_OBYEKTIVKA}:{uid_i}"])
            if rid:
                try:
                    db_set_paid_doc_request_status(int(rid), "approved")
                except Exception:
                    logger.debug("paid_doc_request approve skip rid=%s", rid, exc_info=True)
            try:
                from bot.services.user_service import invalidate_user_profile_cache

                invalidate_user_profile_cache(uid_i)
            except Exception:
                pass
        except Exception:
            logger.warning("payment approve side-effects failed pid=%s", payment_id, exc_info=True)

    if uid is not None:
        try:
            uid_i = int(uid)
            base = (context.bot_data.get("webapp_base") or os.getenv("WEBAPP_BASE") or "").strip()
            from bot.services.bot_notify import (
                notify_payment_approved,
                notify_payment_rejected,
            )

            kind = pdkind or ("cv" if plan == "cv" else "obyektivka" if plan == "objective" else "cv")
            if new_status == "approved":
                await notify_payment_approved(
                    context.bot,
                    uid_i,
                    kind=kind,
                    request_id=rid,
                    webapp_base=base,
                )
            else:
                await notify_payment_rejected(
                    context.bot,
                    uid_i,
                    kind=kind,
                    request_id=rid,
                )
        except Exception:
            logger.warning("payment user notify failed pid=%s", payment_id, exc_info=True)

    msg = "✅ To'lov tasdiqlandi." if new_status == "approved" else "❌ To'lov rad etildi."

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
