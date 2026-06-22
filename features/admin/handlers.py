"""Admin panel — users, payments, broadcast, stats, export."""
from __future__ import annotations

import logging
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from config.settings import settings
from database.repositories import admin_stats as stats_repo
from database.repositories import error_logs as error_logs_repo
from database.repositories import generated_files as files_repo
from database.repositories import payments as payments_repo
from database.repositories import users as users_repo
from features.admin import service as admin_service
from features.admin.keyboards import (
    broadcast_confirm_kb,
    error_filter_kb,
    export_kb,
    payment_filter_kb,
    user_profile_kb,
    user_search_results_kb,
)
from features.admin.states import AdminStates
from features.payment import service as payment_service
from shared.async_db import run as db_run
from shared.keyboards import (
    ADMIN_BTN_BROADCAST,
    ADMIN_BTN_CLOSE,
    ADMIN_BTN_ERRORS,
    ADMIN_BTN_EXPORT,
    ADMIN_BTN_FILES,
    ADMIN_BTN_PAYMENTS,
    ADMIN_BTN_SEARCH,
    ADMIN_BTN_STATS,
    ADMIN_BTN_TOP,
    ADMIN_BTN_USERS,
    admin_menu,
    payment_review_kb,
    user_menu,
)
from shared.payment_notifications import (
    build_payment_notification_text,
    build_pending_payments_list,
)

logger = logging.getLogger(__name__)
router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_user_ids


def _stop_dashboard(message: Message) -> None:
    if message.from_user:
        from features.admin.dashboard import stop_dashboard

        stop_dashboard(message.from_user.id)


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
        try:
            await message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        try:
            await message.answer(text)
        except Exception:
            pass


async def _send_payment_rows(message: Message, rows: list[dict]) -> None:
    if not rows:
        await message.answer("To'lovlar topilmadi.")
        return
    summary = build_pending_payments_list(rows[:10])
    if summary:
        await message.answer(summary)
    for p in rows[:10]:
        pid = int(p["id"])
        purchase_number = payments_repo.count_user_payments(int(p.get("user_id") or 0))
        kind = str(p.get("document_type") or "manual")
        text = build_payment_notification_text(
            p,
            kind=kind,
            purchase_number=purchase_number,
        )
        receipt = p.get("receipt_path")
        st = str(p.get("status") or "").upper()
        kb = payment_review_kb(pid) if st == "PENDING" else None
        if receipt and Path(receipt).is_file():
            await message.answer_photo(FSInputFile(receipt), caption=text, reply_markup=kb)
        else:
            await message.answer(text, reply_markup=kb)


@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        await message.answer("⛔ Faqat admin uchun.")
        return
    await state.clear()
    from features.admin.dashboard import start_dashboard

    await start_dashboard(
        message.bot,
        admin_id=message.from_user.id,
        chat_id=message.chat.id,
    )
    await message.answer("📋 Boshqaruv paneli:", reply_markup=admin_menu())


@router.message(F.text == ADMIN_BTN_CLOSE)
async def admin_close(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    from features.admin.dashboard import stop_dashboard

    stop_dashboard(message.from_user.id)
    await state.clear()
    await message.answer("Admin panel yopildi.", reply_markup=user_menu())


@router.message(F.text == ADMIN_BTN_USERS)
async def admin_users(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    await state.clear()
    rows = users_repo.list_users(20)
    if not rows:
        await message.answer("Foydalanuvchilar yo'q.")
        return
    lines = ["<b>Foydalanuvchilar (oxirgi 20):</b>\n"]
    for u in rows:
        uname = u.get("username") or "No Username"
        if uname != "No Username":
            uname = f"@{uname}"
        lines.append(
            f"• <code>{u['telegram_id']}</code> | {uname} | {u.get('first_name') or '-'}"
        )
    lines.append("\n🔍 Aniq qidirish uchun «Qidirish» tugmasini bosing.")
    await message.answer("\n".join(lines))


@router.message(F.text == ADMIN_BTN_SEARCH)
async def admin_search_prompt(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.user_search)
    await message.answer(
        "🔍 Qidirish:\n"
        "@username, user_id yoki ism kiriting."
    )


@router.message(AdminStates.user_search, F.text)
async def admin_search_run(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    query = (message.text or "").strip()
    await state.clear()
    rows = users_repo.search_users(query, limit=10)
    if not rows:
        await message.answer("Hech narsa topilmadi.", reply_markup=admin_menu())
        return
    if len(rows) == 1:
        profile = users_repo.get_profile_stats(int(rows[0]["telegram_id"]))
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


@router.message(F.text == ADMIN_BTN_STATS)
async def admin_stats(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(admin_service.build_today_stats_text())


@router.message(F.text == ADMIN_BTN_TOP)
async def admin_top(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    await state.clear()
    rows = stats_repo.top_payers(10)
    await message.answer(admin_service.build_top_users_text(rows))


@router.message(F.text == ADMIN_BTN_BROADCAST)
async def admin_broadcast_prompt(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.broadcast_text)
    await message.answer("📢 Barcha foydalanuvchilarga yuboriladigan xabar matnini yozing:")


@router.message(AdminStates.broadcast_text, F.text)
async def admin_broadcast_preview(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
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


@router.message(F.text == ADMIN_BTN_EXPORT)
async def admin_export_menu(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("📥 Export — faylni tanlang:", reply_markup=export_kb())


@router.message(F.text == ADMIN_BTN_ERRORS)
async def admin_errors(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    await state.clear()
    rows = error_logs_repo.list_recent(20)
    await message.answer(
        admin_service.build_error_log_text(rows),
        reply_markup=error_filter_kb(),
    )


@router.message(F.text == ADMIN_BTN_PAYMENTS)
async def admin_payments(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("💳 To'lovlar — filtr tanlang:", reply_markup=payment_filter_kb())


@router.message(F.text == ADMIN_BTN_FILES)
async def admin_files(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    await state.clear()
    rows = files_repo.list_all(20)
    if not rows:
        await message.answer("Yaratilgan fayllar yo'q.")
        return
    lines = ["<b>Yaratilgan fayllar (oxirgi 20):</b>\n"]
    for f in rows:
        lines.append(
            f"• #{f['id']} {f['file_type']} — <code>{f.get('telegram_id')}</code> "
            f"— {f.get('file_name') or '-'}"
        )
    await message.answer("\n".join(lines))


@router.message(AdminStates.credit_amount, F.text)
async def admin_credit_amount(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
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
        credits = users_repo.add_credits(tid, amount)
        await message.answer(f"✅ +{amount} kredit. Jami: {credits}", reply_markup=admin_menu())
    else:
        credits = users_repo.remove_credits(tid, amount)
        await message.answer(f"✅ -{amount} kredit. Jami: {credits}", reply_markup=admin_menu())


@router.message(AdminStates.dm_user_text, F.text)
async def admin_dm_user(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
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
        await message.answer(f"❌ Yuborib bo'lmadi: {exc}", reply_markup=admin_menu())


@router.message(AdminStates.support_reply, F.text)
async def admin_support_reply(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
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
        await message.answer(f"✅ Javob yuborildi (<code>{tid}</code>).")
    except Exception as exc:
        await message.answer(f"❌ Yuborib bo'lmadi: {exc}")


@router.callback_query(F.data == "adm_bc_confirm")
async def broadcast_confirm(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or not _is_admin(query.from_user.id):
        await query.answer("Faqat admin.", show_alert=True)
        return
    data = await state.get_data()
    text = str(data.get("broadcast_text") or "")
    await state.clear()
    if not text or not query.message:
        await query.answer("Matn yo'q.", show_alert=True)
        return
    await query.answer()
    await query.message.edit_reply_markup(reply_markup=None)
    await query.message.answer("📢 Yuborilmoqda...")
    stats = await admin_service.run_broadcast(query.bot, text)
    await query.message.answer(
        f"<b>📢 Broadcast yakunlandi</b>\n\n"
        f"Yuborildi: {stats['sent']}\n"
        f"Muvaffaqiyatli: {stats['success']}\n"
        f"Bloklagan: {stats['blocked']}"
    )


@router.callback_query(F.data == "adm_bc_cancel")
async def broadcast_cancel(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or not _is_admin(query.from_user.id):
        return
    await state.clear()
    await query.answer("Bekor qilindi.")
    if query.message:
        await query.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data.startswith("adm_exp_"))
async def export_callback(query: CallbackQuery) -> None:
    if not query.from_user or not _is_admin(query.from_user.id):
        await query.answer("Faqat admin.", show_alert=True)
        return
    await query.answer("Tayyorlanmoqda...")
    kind = (query.data or "").replace("adm_exp_", "")
    try:
        if kind == "users":
            path = admin_service.build_users_xlsx()
            caption = "Users.xlsx"
        elif kind == "payments":
            path = admin_service.build_payments_xlsx()
            caption = "Payments.xlsx"
        else:
            path = admin_service.build_statistics_xlsx()
            caption = "Statistics.xlsx"
        if query.message:
            await query.message.answer_document(FSInputFile(path), caption=caption)
    except Exception as exc:
        logger.exception("Export failed: %s", exc)
        if query.message:
            await query.message.answer(f"❌ Export xatosi: {exc}")


@router.callback_query(F.data.startswith("adm_pay_"))
async def payment_filter_callback(query: CallbackQuery) -> None:
    if not query.from_user or not _is_admin(query.from_user.id):
        await query.answer("Faqat admin.", show_alert=True)
        return
    await query.answer()
    key = (query.data or "").replace("adm_pay_", "")
    period = None
    status = None
    if key == "today":
        period = "today"
    elif key == "week":
        period = "week"
    elif key == "month":
        period = "month"
    elif key == "all":
        pass
    elif key in ("pending", "approved", "rejected"):
        status = key.upper()
    rows = payments_repo.list_filtered(period=period, status=status, limit=15)
    if key == "all" and not period and not status:
        rows = payments_repo.list_filtered(limit=15)
    if query.message:
        await query.message.answer(f"<b>Filtr:</b> {key} ({len(rows)} ta)")
        await _send_payment_rows(query.message, rows)


@router.callback_query(F.data.startswith("adm_user_"))
async def user_profile_callback(query: CallbackQuery) -> None:
    if not query.from_user or not _is_admin(query.from_user.id):
        await query.answer("Faqat admin.", show_alert=True)
        return
    try:
        tid = int((query.data or "").replace("adm_user_", ""))
    except ValueError:
        await query.answer("ID xato.", show_alert=True)
        return
    profile = users_repo.get_profile_stats(tid)
    if not profile:
        await query.answer("Topilmadi.", show_alert=True)
        return
    await query.answer()
    if query.message:
        await query.message.answer(
            admin_service.build_profile_text(profile),
            reply_markup=user_profile_kb(tid),
        )


@router.callback_query(
    F.data.startswith("adm_cred_add_")
    | F.data.startswith("adm_cred_sub_")
    | F.data.startswith("adm_block_")
    | F.data.startswith("adm_unblock_")
    | F.data.startswith("adm_msg_")
)
async def user_action_callback(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or not _is_admin(query.from_user.id):
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
        users_repo.set_blocked(tid, True)
        if query.message:
            await query.message.answer(f"🚫 <code>{tid}</code> bloklandi.")
    elif action_key == "adm_unblock":
        users_repo.set_blocked(tid, False)
        if query.message:
            await query.message.answer(f"✅ <code>{tid}</code> blokdan chiqarildi.")
    elif action_key == "adm_msg":
        await state.set_state(AdminStates.dm_user_text)
        await state.update_data(dm_target=tid)
        if query.message:
            await query.message.answer(f"<code>{tid}</code> ga yuboriladigan xabarni yozing:")


@router.callback_query(F.data.startswith("sup_reply_"))
async def support_reply_start(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or not _is_admin(query.from_user.id):
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
    if not query.from_user or not _is_admin(query.from_user.id):
        await query.answer("Faqat admin.", show_alert=True)
        return
    key = (query.data or "").replace("adm_err_", "")
    category = None if key == "all" else key
    rows = error_logs_repo.list_recent(20, category=category)
    title = f"Xatolar ({key})"
    await query.answer()
    if query.message:
        await query.message.answer(
            admin_service.build_error_log_text(rows, title=title),
            reply_markup=error_filter_kb(),
        )


@router.callback_query(F.data.startswith("pay_approve_") | F.data.startswith("pay_reject_"))
async def payment_callback(query: CallbackQuery) -> None:
    if not query.from_user or not _is_admin(query.from_user.id):
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

    if action == "approve":
        result = await db_run(payment_service.approve_payment, pid)
        if result:
            tid = int(result["telegram_id"])
            credits = await db_run(users_repo.get_credits, tid)
            await _update_payment_review_message(
                query.message,
                f"✅ To'lov #{pid} tasdiqlandi.\n"
                f"Foydalanuvchi pul balansi: {credits} ta hujjat",
            )
            await query.bot.send_message(
                tid,
                f"✅ To'lovingiz tasdiqlandi!\n"
                f"💳 Pul balansi: <b>{credits}</b> ta hujjat\n"
                f"ℹ️ Har biri CV <b>yoki</b> Obyektivka uchun.",
            )
        elif query.message:
            await query.message.reply("Tasdiqlash xatosi.")
    else:
        ok = await db_run(payment_service.reject_payment, pid)
        if ok:
            payment = await db_run(payments_repo.get_payment, pid)
            await _update_payment_review_message(
                query.message,
                f"❌ To'lov #{pid} rad etildi.",
            )
            if payment:
                await query.bot.send_message(
                    int(payment["telegram_id"]),
                    "❌ To'lovingiz rad etildi. Qayta urinib ko'ring.",
                )
        elif query.message:
            await query.message.reply("Rad etish xatosi.")
