"""Admin panel — dashboard, callbacks, FSM flows."""
from __future__ import annotations

import asyncio
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from config.settings import settings
from database.repositories import admin_logs as admin_logs_repo
from database.repositories import error_logs as error_logs_repo
from database.repositories import payments as payments_repo
from database.repositories import admin_stats as stats_repo
from database.repositories import users as users_repo
from features.admin import actions as admin_actions
from features.admin import service as admin_service
from features.admin.dispatch import dispatch_admin_menu, is_admin
from shared.payment_test_filter import filter_real_users, is_test_payment, is_test_user
from features.admin.keyboards import (
    broadcast_confirm_kb,
    error_filter_kb,
    payment_filter_kb,
    user_profile_kb,
    user_search_results_kb,
)
from features.admin.states import AdminStates
from features.payment import service as payment_service
from features.payment.auto_approve_scheduler import cancel_auto_approve
from shared.payment_notifications import build_payment_notification_text
from shared.payment_review_messages import clear_payment_review_messages
from shared.async_db import run as db_run
from shared.keyboards import admin_menu, is_admin_menu_button

logger = logging.getLogger(__name__)
router = Router()

_NOT_MENU = ~F.text.func(is_admin_menu_button)


def _is_undeliverable_telegram_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(
        part in msg
        for part in (
            "chat not found",
            "bot was blocked",
            "user is deactivated",
            "peer_id_invalid",
            "have no rights to send",
        )
    )


async def _update_payment_review_message(message: Message | None, text: str) -> None:
    if not message:
        return
    try:
        if message.photo:
            await message.edit_caption(caption=text, reply_markup=None)
            return
        if message.text:
            await message.edit_text(text, reply_markup=None)
            return
        await message.edit_reply_markup(reply_markup=None)
        await message.answer(text)
    except Exception as exc:
        logger.warning("Payment review message update failed: %s", exc)


async def _notify_payment_user(
    bot,
    telegram_id: int,
    text: str,
    *,
    reply_markup=None,
) -> bool:
    tid = int(telegram_id)
    if is_test_user({"telegram_id": tid}):
        logger.info("Payment notify skipped for test telegram_id=%s", tid)
        return False
    try:
        await bot.send_message(tid, text, reply_markup=reply_markup)
        return True
    except (TelegramBadRequest, TelegramForbiddenError, TelegramAPIError) as exc:
        if _is_undeliverable_telegram_error(exc):
            logger.warning("Payment notify skipped (%s): telegram_id=%s", exc, tid)
            return False
        raise
    except Exception as exc:
        if _is_undeliverable_telegram_error(exc):
            logger.warning("Payment notify skipped (%s): telegram_id=%s", exc, tid)
            return False
        raise


# ── Global admin menu (har qanday FSM holatidan ishlaydi) ─────────────────

@router.message(F.text.func(is_admin_menu_button))
async def admin_menu_router(message: Message, state: FSMContext) -> None:
    await dispatch_admin_menu(message, state)


@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        await message.answer("⛔ Faqat admin uchun.")
        return
    try:
        await state.clear()
        from features.admin.dashboard import start_dashboard

        await start_dashboard(
            message.bot,
            admin_id=message.from_user.id,
            chat_id=message.chat.id,
        )
        await message.answer("📋 Boshqaruv paneli:", reply_markup=admin_menu())
        logger.info("Admin panel opened: user=%s", message.from_user.id)
    except Exception as exc:
        logger.exception("Admin panel open failed: %s", exc)
        await message.answer(f"❌ Dashboard ochilmadi: {exc}", reply_markup=admin_menu())


# ── FSM flows (menyu tugmalaridan tashqari matn) ──────────────────────────

@router.message(AdminStates.user_search, _NOT_MENU, F.text)
async def admin_search_run(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    query = (message.text or "").strip()
    try:
        await state.clear()
        rows = await asyncio.to_thread(stats_repo.search_users_enriched, query, 10)
        rows = filter_real_users(rows)
        if not rows:
            await message.answer("Hech narsa topilmadi.", reply_markup=admin_menu())
            return
        if len(rows) == 1:
            profile = await asyncio.to_thread(
                users_repo.get_profile_stats, int(rows[0]["telegram_id"])
            )
            if profile:
                await message.answer(
                    admin_service.build_profile_text(profile),
                    reply_markup=user_profile_kb(int(profile["telegram_id"])),
                )
                return
        await message.answer(
            f"<b>{len(rows)} ta natija:</b>",
            reply_markup=user_search_results_kb(rows),
        )
    except Exception as exc:
        logger.exception("Admin search failed: %s", exc)
        await message.answer(f"❌ Qidiruv xatosi: {exc}", reply_markup=admin_menu())


@router.message(AdminStates.broadcast_text, _NOT_MENU, F.text)
async def admin_broadcast_preview(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    text = (message.text or "").strip()
    if not text:
        await message.answer("Matn bo'sh.")
        return
    await state.update_data(broadcast_text=text)
    await message.answer(
        f"<b>Oldindan ko'rish:</b>\n\n{text}\n\nYuborilsinmi?",
        reply_markup=broadcast_confirm_kb(),
    )


@router.message(AdminStates.credit_amount, _NOT_MENU, F.text)
async def admin_credit_amount(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    await state.clear()
    try:
        amount = max(1, int((message.text or "").strip()))
    except ValueError:
        await message.answer("Raqam kiriting.", reply_markup=admin_menu())
        return
    tid = int(data.get("credit_target") or 0)
    action = data.get("credit_action")
    if not tid:
        await message.answer("Foydalanuvchi topilmadi.", reply_markup=admin_menu())
        return
    if action == "add":
        credits = await asyncio.to_thread(users_repo.add_credits, tid, amount)
        await message.answer(f"✅ +{amount} kredit. Jami: {credits}", reply_markup=admin_menu())
    else:
        credits = await asyncio.to_thread(users_repo.remove_credits, tid, amount)
        await message.answer(f"✅ -{amount} kredit. Jami: {credits}", reply_markup=admin_menu())
    logger.info("Admin credit %s %s for %s", action, amount, tid)


@router.message(AdminStates.dm_user_text, _NOT_MENU, F.text)
async def admin_dm_user(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    await state.clear()
    tid = int(data.get("dm_target") or 0)
    text = (message.text or "").strip()
    if not tid or not text:
        await message.answer("Xatolik.", reply_markup=admin_menu())
        return
    try:
        await message.bot.send_message(tid, text)
        await message.answer(f"✅ Xabar yuborildi (<code>{tid}</code>).", reply_markup=admin_menu())
    except Exception as exc:
        logger.exception("Admin DM failed: %s", exc)
        await message.answer(f"❌ Yuborib bo'lmadi: {exc}", reply_markup=admin_menu())


@router.message(AdminStates.support_reply, _NOT_MENU, F.text)
async def admin_support_reply(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    await state.clear()
    tid = int(data.get("support_target") or 0)
    text = (message.text or "").strip()
    if not tid or not text:
        await message.answer("Xatolik.", reply_markup=admin_menu())
        return
    try:
        await message.bot.send_message(
            tid,
            f"📩 <b>Dastyor AI Support</b>\n\n{text}",
        )
        await message.answer(f"✅ Javob yuborildi (<code>{tid}</code>).", reply_markup=admin_menu())
    except Exception as exc:
        logger.exception("Support reply failed: %s", exc)
        await message.answer(f"❌ Yuborib bo'lmadi: {exc}", reply_markup=admin_menu())


# ── Inline callbacks ──────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_bc_confirm")
async def broadcast_confirm(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or not is_admin(query.from_user.id):
        await query.answer("Faqat admin.", show_alert=True)
        return
    data = await state.get_data()
    text = str(data.get("broadcast_text") or "")
    await state.clear()
    if not text or not query.message:
        await query.answer("Matn yo'q.", show_alert=True)
        return
    await query.answer()
    try:
        await query.message.edit_reply_markup(reply_markup=None)
        await query.message.answer("📢 Yuborilmoqda...")
        stats = await admin_service.run_broadcast(query.bot, text)
        await query.message.answer(
            f"<b>📢 Broadcast yakunlandi</b>\n\n"
            f"Yuborildi: {stats['sent']}\n"
            f"Muvaffaqiyatli: {stats['success']}\n"
            f"Bloklagan: {stats['blocked']}"
        )
    except Exception as exc:
        logger.exception("Broadcast failed: %s", exc)
        await query.message.answer(f"❌ Broadcast xatosi: {exc}")


@router.callback_query(F.data == "adm_bc_cancel")
async def broadcast_cancel(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or not is_admin(query.from_user.id):
        return
    await state.clear()
    await query.answer("Bekor qilindi.")
    if query.message:
        await query.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data.startswith("adm_exp_"))
async def export_callback(query: CallbackQuery) -> None:
    if not query.from_user or not is_admin(query.from_user.id):
        await query.answer("Faqat admin.", show_alert=True)
        return
    await query.answer("Tayyorlanmoqda...")
    kind = (query.data or "").replace("adm_exp_", "")
    try:
        if kind == "users":
            path = await asyncio.to_thread(admin_service.build_users_xlsx)
            caption = "users.xlsx"
        elif kind == "payments":
            path = await asyncio.to_thread(admin_service.build_payments_xlsx)
            caption = "payments.xlsx"
        else:
            path = await asyncio.to_thread(admin_service.build_statistics_xlsx)
            caption = "statistics.xlsx"
        if query.message:
            await query.message.answer_document(FSInputFile(path), caption=caption)
    except Exception as exc:
        logger.exception("Export failed: %s", exc)
        if query.message:
            await query.message.answer(f"❌ Export xatosi: {exc}")


@router.callback_query(F.data.startswith("adm_pay_"))
async def payment_filter_callback(query: CallbackQuery) -> None:
    if not query.from_user or not is_admin(query.from_user.id):
        await query.answer("Faqat admin.", show_alert=True)
        return
    await query.answer()
    if not query.message:
        return
    key = (query.data or "").replace("adm_pay_", "")
    period = None
    status = None
    title = key
    if key == "today":
        period = "today"
        title = "Bugungi to'lovlar"
    elif key == "week":
        period = "week"
        title = "Haftalik to'lovlar"
    elif key == "month":
        period = "month"
        title = "Oylik to'lovlar"
    elif key in ("pending", "approved", "rejected"):
        status = key.upper()
        title = f"{status} to'lovlar"
    elif key == "all":
        title = "Barcha to'lovlar"
    try:
        from features.admin.formatters import build_payments_list_text

        rows = await asyncio.to_thread(
            stats_repo.list_payments_enriched,
            period=period,
            status=status,
            limit=15,
        )
        if not rows:
            await query.message.answer(
                f"💳 {title}: to'lovlar topilmadi.",
                reply_markup=admin_menu(),
            )
            return
        text = build_payments_list_text(rows, title=title)
        await query.message.answer(text, reply_markup=payment_filter_kb())
        if status == "PENDING":
            await admin_actions._send_payment_rows(query.message, rows)
    except Exception as exc:
        logger.exception("Payment filter failed: %s", exc)
        await query.message.answer(f"❌ To'lovlar xatosi: {exc}")


@router.callback_query(F.data.startswith("adm_user_"))
async def user_profile_callback(query: CallbackQuery) -> None:
    if not query.from_user or not is_admin(query.from_user.id):
        await query.answer("Faqat admin.", show_alert=True)
        return
    try:
        tid = int((query.data or "").replace("adm_user_", ""))
    except ValueError:
        await query.answer("ID xato.", show_alert=True)
        return
    try:
        profile = await asyncio.to_thread(users_repo.get_profile_stats, tid)
        if not profile:
            await query.answer("Topilmadi.", show_alert=True)
            return
        await query.answer()
        if query.message:
            await query.message.answer(
                admin_service.build_profile_text(profile),
                reply_markup=user_profile_kb(tid),
            )
    except Exception as exc:
        logger.exception("Profile load failed: %s", exc)
        await query.answer("Xatolik.", show_alert=True)
        if query.message:
            await query.message.answer(f"❌ Profil xatosi: {exc}")


@router.callback_query(
    F.data.startswith("adm_cred_add_")
    | F.data.startswith("adm_cred_sub_")
    | F.data.startswith("adm_block_")
    | F.data.startswith("adm_unblock_")
    | F.data.startswith("adm_msg_")
)
async def user_action_callback(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or not is_admin(query.from_user.id):
        await query.answer("Faqat admin.", show_alert=True)
        return
    data = query.data or ""
    parts = data.rsplit("_", 1)
    if len(parts) != 2:
        await query.answer("Xato.", show_alert=True)
        return
    action_key, tid_s = parts[0], parts[1]
    try:
        tid = int(tid_s)
    except ValueError:
        await query.answer("ID xato.", show_alert=True)
        return
    await query.answer()
    try:
        if action_key == "adm_cred_add":
            await state.set_state(AdminStates.credit_amount)
            await state.update_data(credit_target=tid, credit_action="add")
            if query.message:
                await query.message.answer(f"<code>{tid}</code> uchun nechta kredit qo'shilsin?")
        elif action_key == "adm_cred_sub":
            await state.set_state(AdminStates.credit_amount)
            await state.update_data(credit_target=tid, credit_action="sub")
            if query.message:
                await query.message.answer(f"<code>{tid}</code> dan nechta kredit olib tashlansin?")
        elif action_key == "adm_block":
            await asyncio.to_thread(users_repo.set_blocked, tid, True)
            if query.from_user:
                admin_logs_repo.record(query.from_user.id, "user_block", f"telegram_id={tid}")
            if query.message:
                await query.message.answer(f"🚫 <code>{tid}</code> bloklandi.")
        elif action_key == "adm_unblock":
            await asyncio.to_thread(users_repo.set_blocked, tid, False)
            if query.from_user:
                admin_logs_repo.record(query.from_user.id, "user_unblock", f"telegram_id={tid}")
            if query.message:
                await query.message.answer(f"✅ <code>{tid}</code> blokdan chiqarildi.")
        elif action_key == "adm_msg":
            await state.set_state(AdminStates.dm_user_text)
            await state.update_data(dm_target=tid)
            if query.message:
                await query.message.answer(f"<code>{tid}</code> ga yuboriladigan xabarni yozing:")
    except Exception as exc:
        logger.exception("User action failed: %s", exc)
        if query.message:
            await query.message.answer(f"❌ Amal xatosi: {exc}")


@router.callback_query(F.data.startswith("sup_reply_"))
async def support_reply_start(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or not is_admin(query.from_user.id):
        await query.answer("Faqat admin.", show_alert=True)
        return
    try:
        tid = int((query.data or "").replace("sup_reply_", ""))
    except ValueError:
        await query.answer("ID xato.", show_alert=True)
        return
    await query.answer()
    await state.set_state(AdminStates.support_reply)
    await state.update_data(support_target=tid)
    if query.message:
        await query.message.reply(f"📩 <code>{tid}</code> ga javob matnini yozing:")


@router.callback_query(F.data.startswith("adm_err_"))
async def error_filter_callback(query: CallbackQuery) -> None:
    if not query.from_user or not is_admin(query.from_user.id):
        await query.answer("Faqat admin.", show_alert=True)
        return
    key = (query.data or "").replace("adm_err_", "")
    category = None if key == "all" else key
    await query.answer()
    try:
        rows = await asyncio.to_thread(error_logs_repo.list_recent, 20, category)
        title = f"Xatolar ({key})"
        if query.message:
            await query.message.answer(
                admin_service.build_error_log_text(rows, title=title),
                reply_markup=error_filter_kb(),
            )
    except Exception as exc:
        logger.exception("Error filter failed: %s", exc)
        if query.message:
            await query.message.answer(f"❌ Xatolar yuklanmadi: {exc}")


@router.callback_query(F.data.startswith("pay_approve_") | F.data.startswith("pay_reject_"))
async def payment_callback(query: CallbackQuery) -> None:
    if not query.from_user or not is_admin(query.from_user.id):
        await query.answer("Faqat admin.", show_alert=True)
        return
    await query.answer()

    parts = (query.data or "").split("_")
    if len(parts) != 3:
        if query.message:
            await query.message.reply("Noto'g'ri callback.")
        return

    action, pid_s = parts[1], parts[2]
    try:
        pid = int(pid_s)
    except ValueError:
        if query.message:
            await query.message.reply("ID xato.")
        return

    try:
        payment_before = await db_run(payments_repo.get_payment, pid)
        if payment_before and is_test_payment(payment_before):
            cancel_auto_approve(pid)
            if action == "approve":
                result = await db_run(
                    payment_service.approve_payment,
                    pid,
                    None,
                    approved_by=query.from_user.id,
                )
                if result and query.message:
                    msg = (
                        f"✅ To'lov #{pid} allaqachon tasdiqlangan (test akkaunt)."
                        if result.get("already_approved")
                        else f"✅ To'lov #{pid} tasdiqlandi (test akkaunt — foydalanuvchiga xabar yuborilmaydi)."
                    )
                    await _update_payment_review_message(query.message, msg)
                elif query.message:
                    await _update_payment_review_message(
                        query.message,
                        f"✅ To'lov #{pid} allaqachon ko'rib chiqilgan (test akkaunt).",
                    )
            else:
                ok = await db_run(payment_service.reject_payment, pid)
                if ok and query.message:
                    await _update_payment_review_message(
                        query.message,
                        f"❌ To'lov #{pid} rad etildi (test akkaunt).",
                    )
                elif query.message:
                    await query.message.reply("Rad etish xatosi.")
            return

        cancel_auto_approve(pid)
        if action == "approve":
            result = await db_run(
                payment_service.approve_payment,
                pid,
                None,
                approved_by=query.from_user.id,
            )
            if result:
                clear_payment_review_messages(pid)
                admin_logs_repo.record(
                    query.from_user.id,
                    "payment_approve",
                    f"payment_id={pid}",
                )
                tid = int(result["telegram_id"])
                credits = await db_run(users_repo.get_credits, tid)
                if result.get("already_approved"):
                    if query.message:
                        await _update_payment_review_message(
                            query.message,
                            f"✅ To'lov #{pid} allaqachon tasdiqlangan! (Balans: {credits} ta)",
                        )
                    return

                from shared.keyboards import open_services_after_payment_inline
                from shared.marketing import payment_approved_message

                doc_type = str(result.get("document_type") or "cv")
                promo_bonus = int(result.get("promo_bonus_granted") or 0)
                notified = await _notify_payment_user(
                    query.bot,
                    tid,
                    payment_approved_message(credits, doc_type, promo_bonus=promo_bonus),
                    reply_markup=open_services_after_payment_inline(tid, doc_type),
                )
                ref_info = result.get("referral_info")
                if ref_info:
                    from shared.referral import notify_referrer

                    await notify_referrer(query.bot, ref_info, event="payment")
                purchase_number = await db_run(
                    payments_repo.count_user_payments, int(result.get("user_id") or 0)
                )
                kind = str(result.get("document_type") or "manual")
                resolved = build_payment_notification_text(
                    result,
                    kind=kind,
                    purchase_number=int(purchase_number or 1),
                    auto_approved=True,
                    credits=credits,
                )
                delivery_note = (
                    "\n📨 Foydalanuvchiga xabar yuborildi."
                    if notified
                    else "\nℹ️ Foydalanuvchiga xabar yetkazilmadi (chat topilmadi)."
                )
                await _update_payment_review_message(
                    query.message,
                    f"{resolved}{delivery_note}",
                )
            elif query.message:
                await _update_payment_review_message(
                    query.message,
                    f"✅ To'lov #{pid} allaqachon ko'rib chiqilgan.",
                )
        else:
            ok = await db_run(payment_service.reject_payment, pid)
            if ok:
                clear_payment_review_messages(pid)
                admin_logs_repo.record(
                    query.from_user.id,
                    "payment_reject",
                    f"payment_id={pid}",
                )
                payment = await db_run(payments_repo.get_payment, pid)
                notified = False
                if payment:
                    doc_type = str(payment.get("document_type") or "manual")
                    from shared.keyboards import payment_rejected_keyboard

                    notified = await _notify_payment_user(
                        query.bot,
                        int(payment["telegram_id"]),
                        "❌ <b>To'lovingiz rad etildi.</b>\n\n"
                        "Chek aniq emas yoki to'lov tasdiqlanmadi. Qayta urinib ko'ring.",
                        reply_markup=payment_rejected_keyboard(
                            int(payment["telegram_id"]),
                            document_type=doc_type,
                        ),
                    )
                delivery_note = (
                    "\n📨 Foydalanuvchiga xabar yuborildi."
                    if notified
                    else "\nℹ️ Foydalanuvchiga xabar yetkazilmadi (chat topilmadi)."
                )
                resolved = ""
                if payment:
                    purchase_number = await db_run(
                        payments_repo.count_user_payments, int(payment.get("user_id") or 0)
                    )
                    kind = str(payment.get("document_type") or "manual")
                    resolved = build_payment_notification_text(
                        payment,
                        kind=kind,
                        purchase_number=int(purchase_number or 1),
                        rejected=True,
                    )
                await _update_payment_review_message(
                    query.message,
                    f"{resolved or f'❌ To\'lov #{pid} rad etildi.'}{delivery_note}",
                )
            elif query.message:
                await query.message.reply("Rad etish xatosi.")
    except Exception as exc:
        logger.exception("Payment callback failed: %s", exc)
        if _is_undeliverable_telegram_error(exc):
            if query.message:
                await query.message.reply(
                    "ℹ️ To'lov holati yangilandi, lekin foydalanuvchiga xabar yetkazilmadi."
                )
            return
        from shared.error_log import record_error

        record_error("payment", f"Admin callback #{pid}: {exc}")
        if query.message:
            await query.message.reply(f"❌ To'lov amali xatosi: {exc}")
