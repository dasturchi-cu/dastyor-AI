import asyncio
import os
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.keyboards.reply_keyboards import get_back_button
from bot.services.settings_service import get_premium_status, get_premium_expiry, add_premium
from bot.services.plan_limits import reset_plan_quotas_on_activation
from bot.handlers.admin import is_admin
import bot.services.user_service as crm
from bot.services.premium_purchase_db import (
    create_payment_request,
    get_payment_request,
    set_payment_request_status,
    save_subscription,
)
from bot.services.pricing import STANDARD_PRICE_UZS, PREMIUM_PRICE_UZS, format_uzs, apply_percent_discount, REFERRAL_DISCOUNT_PERCENT

CARD_NUMBER = "9860 1201 7225 8424"
CARD_OWNER = "DILNOZA MOMINOVA"
PREMIUM_ADMIN_GROUP_ID = int(os.getenv("PREMIUM_ADMIN_GROUP_ID", "-1003457224552"))
logger = logging.getLogger(__name__)

PLAN_INFO = {
    "standard": {"title": "Standard", "days": 7},
    "premium": {"title": "Premium", "days": 30},
}

# Single-doc paid products (manual approval)
SINGLE_DOC_PRICE_UZS = int(os.getenv("SINGLE_DOC_PRICE_UZS", "5000") or "5000")


def _premium_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📋 Kartani nusxa olish", callback_data="buy_copy_card")],
        ]
    )


def _card_message(plan_title: str, *, discount_percent: int = 0) -> str:
    base = PREMIUM_PRICE_UZS if plan_title.lower() == "premium" else STANDARD_PRICE_UZS
    price = apply_percent_discount(base, discount_percent) if discount_percent else base
    return (
        "💎 <b>Premium sotib olish</b>\n\n"
        "Premium olish uchun quyidagi kartaga to‘lov qiling.\n\n"
        "💳 <b>Karta raqami:</b>\n"
        f"<code>{CARD_NUMBER}</code>\n\n"
        "👤 <b>Karta egasi:</b>\n"
        f"<b>{CARD_OWNER}</b>\n\n"
        "To‘lov qilgandan keyin skrenshotni shu chatga yuboring.\n\n"
        f"📦 Tarif: <b>{plan_title}</b>\n"
        + (f"🎁 Referal chegirma: <b>{int(discount_percent)}%</b>\n" if discount_percent else "")
        + f"💰 Narx: <b>{format_uzs(price)} so'm</b>"
    )


async def premium_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Premium purchase entry point (private chat only)."""
    if not update.effective_chat or update.effective_chat.type != "private":
        return

    uid = update.effective_user.id if update.effective_user else None
    status_line = ""
    if uid:
        st = get_premium_status(uid)
        if st == "active":
            exp = get_premium_expiry(uid) or "-"
            status_line = f"\n\n✅ Sizda faol premium bor. Tugash sanasi: <b>{exp}</b>"
        elif st == "expired":
            status_line = "\n\n⚠️ Premium muddati tugagan. Yangilash mumkin."

    # Default plan unless user selects otherwise elsewhere
    context.user_data["premium_plan"] = context.user_data.get("premium_plan") or "premium"
    context.user_data["waiting_for"] = "premium_payment_screenshot"
    plan_data = PLAN_INFO.get(str(context.user_data.get("premium_plan")).lower(), PLAN_INFO["premium"])
    disc = 0
    try:
        profile = crm.get_user_profile(uid) or {}
        if profile.get("referral_discount_active"):
            disc = int(profile.get("referral_discount_percent") or REFERRAL_DISCOUNT_PERCENT or 0)
    except Exception:
        disc = 0
    await update.message.reply_text(
        _card_message(plan_data["title"], discount_percent=disc),
        parse_mode="HTML",
        reply_markup=_premium_keyboard(),
    )
    if status_line:
        await update.message.reply_text(status_line, parse_mode="HTML", reply_markup=get_back_button())


async def premium_purchase_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline actions for premium purchase card."""
    query = update.callback_query
    if not query:
        return
    await query.answer()

    if not query.message or not query.message.chat or query.message.chat.type != "private":
        return

    data = query.data or ""
    if data == "buy_copy_card":
        # Send plain card number to chat so user can copy easily
        try:
            await query.message.reply_text(CARD_NUMBER)
        except Exception:
            pass
        return

    return


async def handle_premium_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Accept payment screenshot in private chat and forward to admin group.
    Returns True if update was handled.
    """
    if not update.message or not update.effective_user:
        return False
    if not update.effective_chat or update.effective_chat.type != "private":
        return False
    waiting = context.user_data.get("waiting_for")
    if waiting not in {"premium_payment_screenshot", "paid_doc_payment_screenshot"}:
        return False

    has_media = bool(update.message.photo or update.message.document)
    if not has_media:
        await update.message.reply_text("❌ Iltimos, to'lov skrenshotini rasm yoki fayl ko'rinishida yuboring.")
        return True

    is_paid_doc = waiting == "paid_doc_payment_screenshot"
    plan = str(context.user_data.get("premium_plan", "premium")).lower()
    plan_data = PLAN_INFO.get(plan, PLAN_INFO["premium"])
    paid_kind = str(context.user_data.get("paid_doc_kind") or "").strip().lower()
    paid_rid = context.user_data.get("paid_doc_request_id")
    user = update.effective_user

    request_id = None
    try:
        from bot.services.supabase_db import has_db, db_create_payment

        if has_db():
            meta = {
                "source": "telegram_screenshot",
                "username": user.username or "",
                "first_name": user.first_name or "",
            }
            plan_type = plan
            if is_paid_doc:
                # Keep payments.plan_type schema-compatible; single-doc is detected by metadata.
                plan_type = "premium"
                meta["paid_doc_request_id"] = int(paid_rid) if str(paid_rid).isdigit() else None
                meta["paid_doc_kind"] = paid_kind
            pid = db_create_payment(
                int(user.id),
                plan_type,
                float(SINGLE_DOC_PRICE_UZS) if is_paid_doc else 0.0,
                screenshot_url=None,
                metadata=meta,
            )
            if pid is not None:
                request_id = pid
    except Exception as e:
        logger.debug("db_create_payment (telegram): %s", e)

    if request_id is None:
        request_id = create_payment_request(
            user_id=int(user.id),
            plan_type=("premium" if is_paid_doc else plan),
            username=user.username or "",
            first_name=user.first_name or "",
        )

    uname = f"@{user.username}" if user.username else "yo'q"
    review_kb = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"prempay_approve_{request_id}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"prempay_reject_{request_id}"),
        ]]
    )
    if is_paid_doc:
        kind_title = "CV" if paid_kind == "cv" else "Obyektivka"
        caption = (
            "💰 <b>Yangi to‘lov (single)</b>\n\n"
            f"So'rov ID: <code>{request_id}</code>\n"
            f"Username: {uname}\n"
            f"User ID: <code>{user.id}</code>\n"
            f"Xizmat: <b>{kind_title}</b>\n"
            f"Narx: <b>{format_uzs(SINGLE_DOC_PRICE_UZS)} so'm</b>\n"
            f"Doc request: <code>{paid_rid}</code>"
        )
    else:
        caption = (
            "💰 <b>Yangi premium to‘lov</b>\n\n"
            f"So'rov ID: <code>{request_id}</code>\n"
            f"Username: {uname}\n"
            f"User ID: <code>{user.id}</code>\n"
            f"Tarif: <b>{plan_data['title']}</b>\n"
            f"Holat: <b>{plan_data['title']} uchun to'lov qildi</b>"
        )

    context.user_data.pop("waiting_for", None)
    context.user_data.pop("paid_doc_kind", None)
    context.user_data.pop("paid_doc_request_id", None)
    await update.message.reply_text(
        "✅ Skrenshot qabul qilindi. Admin tasdiqlashini kuting — tasdiqdan keyin fayl shu chatga keladi."
        if is_paid_doc
        else "✅ Skrenshot qabul qilindi. Admin tasdiqlashini kuting — tasdiqdan keyin tarif darhol amal qiladi."
    )

    bot = context.bot
    chat_admin = PREMIUM_ADMIN_GROUP_ID

    async def _forward_to_admins():
        try:
            if update.message.photo:
                await bot.send_photo(
                    chat_id=chat_admin,
                    photo=update.message.photo[-1].file_id,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=review_kb,
                )
            else:
                await bot.send_document(
                    chat_id=chat_admin,
                    document=update.message.document.file_id,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=review_kb,
                )
        except Exception as e:
            logger.exception("Premium skrenshot admin guruhiga yuborishda xato: %s", e)
            try:
                await bot.send_message(
                    chat_id=int(user.id),
                    text=(
                        "⚠️ Skrenshot admin guruhiga yuborilmadi. "
                        "Iltimos, support orqali yozing yoki qayta urinib ko'ring.\n"
                        f"So'rov ID: <code>{request_id}</code>"
                    ),
                    parse_mode="HTML",
                )
            except Exception:
                pass

    asyncio.create_task(_forward_to_admins())
    return True


async def premium_payment_review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin group callbacks:
    - prempay_approve_<request_id>
    - prempay_reject_<request_id>
    """
    query = update.callback_query
    if not query:
        return

    data = query.data or ""
    if not data.startswith("prempay_"):
        return

    if not await is_admin(query.from_user.id):
        await query.answer("⛔ Sizda ruxsat yo'q", show_alert=True)
        return

    parts = data.split("_")
    if len(parts) != 3 or not parts[2].isdigit():
        await query.answer("Noto'g'ri callback", show_alert=True)
        return

    action = parts[1]
    request_id = int(parts[2])

    # ── 1) Supabase path (payments id) ─────────────────────────────────────
    try:
        from bot.services.supabase_db import (
            has_db as supa_has_db,
            db_get_payment,
            db_set_payment_status,
            db_activate_subscription,
            db_reset_daily_usage,
            db_consume_referral_discount,
        )
        if supa_has_db():
            pay = db_get_payment(request_id)
            if pay:
                uid = int(pay["user_id"])
                plan = (pay.get("plan_type") or "premium").lower()
                plan_title = "Standart" if plan == "standard" else "Premium"
                days = 7 if plan == "standard" else 30

                if action == "approve":
                    # Mark payment approved
                    db_set_payment_status(request_id, "approved", reviewed_by=int(query.from_user.id))

                    meta = pay.get("metadata") if isinstance(pay.get("metadata"), dict) else {}
                    is_single_doc = bool(meta.get("paid_doc_request_id")) or (str(meta.get("paid_doc_kind") or "").strip().lower() in {"cv", "obyektivka"})
                    # If this is a paid single-doc request, do NOT activate subscription.
                    if is_single_doc:
                        db_set_payment_status(request_id, "approved", reviewed_by=int(query.from_user.id))
                        doc_rid = meta.get("paid_doc_request_id")
                        try:
                            from bot.services.supabase_db import db_get_paid_doc_request, db_set_paid_doc_request_status

                            req_row = db_get_paid_doc_request(int(doc_rid)) if str(doc_rid).isdigit() else None
                            if not req_row or int(req_row.get("user_id") or 0) != uid:
                                raise RuntimeError("paid_doc_request topilmadi")
                            # WebApp will provide download after this.
                            db_set_paid_doc_request_status(int(req_row["id"]), "approved")
                            try:
                                await context.bot.send_message(
                                    chat_id=uid,
                                    text="✅ To'lov tasdiqlandi. Web mini-appga qayting — u yerdan faylni yuklab olasiz.",
                                )
                            except Exception:
                                pass

                        except Exception as e:
                            logger.error("paid_doc approve failed: %s", e, exc_info=True)
                            try:
                                await context.bot.send_message(chat_id=uid, text="⚠️ To'lov tasdiqlandi, lekin so'rov topilmadi. Supportga yozing.")
                            except Exception:
                                pass

                        await query.answer("Tasdiqlandi", show_alert=False)
                        try:
                            new_caption = (query.message.caption or "") + "\n\n✅ Tasdiqlandi"
                            await query.message.edit_caption(caption=new_caption, parse_mode="HTML", reply_markup=None)
                        except Exception:
                            pass
                        return

                    start_dt = datetime.utcnow()
                    expire_dt = start_dt + timedelta(days=days)
                    db_activate_subscription(
                        user_id=uid,
                        plan_type=plan,
                        start_date=start_dt.isoformat(),
                        expire_date=expire_dt.isoformat(),
                        status="active",
                    )
                    db_reset_daily_usage(uid)
                    reset_plan_quotas_on_activation(uid, plan)
                    # 1-time referral discount: consume after successful activation
                    try:
                        db_consume_referral_discount(uid)
                    except Exception:
                        pass

                    meta = pay.get("metadata") if isinstance(pay.get("metadata"), dict) else {}
                    pname = (meta.get("first_name") or "").strip() or "User"
                    puser = (meta.get("username") or "").strip() or ""
                    try:
                        add_premium(uid, days=days, name=pname, username=puser)
                        crm.log_premium_transaction(uid, days, str(query.from_user.id))
                    except Exception as e:
                        logger.debug("add_premium sync (supa path): %s", e)

                    # Notify user
                    end_date_str = expire_dt.strftime("%Y-%m-%d")
                    try:
                        await context.bot.send_message(
                            chat_id=uid,
                            text=(
                                "✅ Premium tarifingiz faollashtirildi\n\n"
                                f"📦 Tarif: {plan_title}\n"
                                f"📅 Tugash sanasi: {end_date_str}"
                            ),
                        )
                    except Exception as e:
                        logger.warning(f"Failed to notify user {uid} on premium approve (supa): {e}")

                    await query.answer("Tasdiqlandi", show_alert=False)
                    try:
                        new_caption = (query.message.caption or "") + "\n\n✅ Tasdiqlandi"
                        await query.message.edit_caption(caption=new_caption, parse_mode="HTML", reply_markup=None)
                    except Exception:
                        pass
                    return

                if action == "reject":
                    db_set_payment_status(request_id, "rejected", reviewed_by=int(query.from_user.id))
                    try:
                        await context.bot.send_message(chat_id=uid, text="❌ To'lov tasdiqlanmadi")
                    except Exception as e:
                        logger.warning(f"Failed to notify user {uid} on premium reject (supa): {e}")

                    await query.answer("Rad etildi", show_alert=False)
                    try:
                        new_caption = (query.message.caption or "") + "\n\n❌ Rad etildi"
                        await query.message.edit_caption(caption=new_caption, parse_mode="HTML", reply_markup=None)
                    except Exception:
                        pass
                    return
    except Exception as e:
        logger.warning(f"Supabase premium review failed, fallback to sqlite: {e}")

    # ── 2) SQLite path (request id) ─────────────────────────────────────────
    req = get_payment_request(request_id)
    if not req:
        await query.answer("So'rov topilmadi", show_alert=True)
        return
    if req.get("status") != "pending":
        await query.answer("Bu so'rov allaqachon ko'rib chiqilgan", show_alert=True)
        return

    uid = int(req["user_id"])
    plan = (req.get("plan_type") or "premium").lower()
    plan_title = "Standart" if plan == "standard" else "Premium"
    days = 7 if plan == "standard" else 30

    if action == "approve":
        ok = set_payment_request_status(request_id, "approved", reviewer_id=int(query.from_user.id))
        if not ok:
            await query.answer("So'rov holatini yangilab bo'lmadi", show_alert=True)
            return

        profile = crm.get_user_profile(uid) or {}
        name = profile.get("first_name") or req.get("first_name") or "User"
        username = profile.get("username") or req.get("username") or ""
        end_date = add_premium(uid, days=days, name=name, username=username)
        crm.log_premium_transaction(uid, days, str(query.from_user.id))

        try:
            from bot.services.supabase_db import has_db as supa_has_db, db_reset_daily_usage

            if supa_has_db():
                db_reset_daily_usage(uid)
        except Exception:
            pass
        reset_plan_quotas_on_activation(uid, plan)

        start_dt = datetime.utcnow()
        expire_dt = start_dt + timedelta(days=days)
        save_subscription(
            user_id=uid,
            plan_type=plan,
            start_date=start_dt.isoformat(),
            expire_date=expire_dt.isoformat(),
        )

        try:
            await context.bot.send_message(
                chat_id=uid,
                text=(
                    "✅ Premium tarifingiz faollashtirildi\n\n"
                    f"📦 Tarif: {plan_title}\n"
                    f"📅 Tugash sanasi: {end_date}"
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to notify user {uid} on premium approve (sqlite): {e}")

        await query.answer("Tasdiqlandi", show_alert=False)
        try:
            new_caption = (query.message.caption or "") + "\n\n✅ Tasdiqlandi"
            await query.message.edit_caption(caption=new_caption, parse_mode="HTML", reply_markup=None)
        except Exception:
            pass
        return

    if action == "reject":
        ok = set_payment_request_status(request_id, "rejected", reviewer_id=int(query.from_user.id))
        if not ok:
            await query.answer("So'rov holatini yangilab bo'lmadi", show_alert=True)
            return
        try:
            await context.bot.send_message(chat_id=uid, text="❌ To'lov tasdiqlanmadi")
        except Exception as e:
            logger.warning(f"Failed to notify user {uid} on premium reject (sqlite): {e}")

        await query.answer("Rad etildi", show_alert=False)
        try:
            new_caption = (query.message.caption or "") + "\n\n❌ Rad etildi"
            await query.message.edit_caption(caption=new_caption, parse_mode="HTML", reply_markup=None)
        except Exception:
            pass
        return
