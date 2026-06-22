"""Admin panel — users, payments, files."""
from __future__ import annotations

import logging
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile, Message

from config.settings import settings
from database.repositories import generated_files as files_repo
from database.repositories import payments as payments_repo
from database.repositories import users as users_repo
from features.payment import service as payment_service
from shared.keyboards import (
    ADMIN_BTN_CLOSE,
    ADMIN_BTN_FILES,
    ADMIN_BTN_PAYMENTS,
    ADMIN_BTN_USERS,
    admin_menu,
    payment_review_kb,
    user_menu,
)

logger = logging.getLogger(__name__)
router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_user_ids


async def _update_payment_review_message(message: Message | None, text: str) -> None:
    """Photo+caption yoki matnli admin xabarini tasdiqlash/rad keyin yangilash."""
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


@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        await message.answer("⛔ Faqat admin uchun.")
        return
    pending = payments_repo.count_pending()
    users = users_repo.count_users()
    await message.answer(
        f"🛠 <b>Admin panel</b>\n\n"
        f"👥 Foydalanuvchilar: {users}\n"
        f"💳 Kutilayotgan to'lovlar: {pending}",
        reply_markup=admin_menu(),
    )


@router.message(F.text == ADMIN_BTN_CLOSE)
async def admin_close(message: Message) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    await message.answer("Admin panel yopildi.", reply_markup=user_menu())


@router.message(F.text == ADMIN_BTN_USERS)
async def admin_users(message: Message) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    rows = users_repo.list_users(20)
    if not rows:
        await message.answer("Foydalanuvchilar yo'q.")
        return
    lines = ["<b>Foydalanuvchilar (oxirgi 20):</b>\n"]
    for u in rows:
        lines.append(
            f"• <code>{u['telegram_id']}</code> — {u.get('first_name') or '-'} "
            f"| kredit: {u.get('credits', 0)}"
        )
    await message.answer("\n".join(lines))


@router.message(F.text == ADMIN_BTN_PAYMENTS)
async def admin_payments(message: Message) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    pending = payment_service.list_pending()
    if not pending:
        await message.answer("Kutilayotgan to'lovlar yo'q.")
        return
    for p in pending[:10]:
        pid = int(p["id"])
        text = (
            f"💳 <b>Yangi to'lov #{pid}</b>\n"
            f"👤 {p.get('payer_name')} (<code>{p.get('telegram_id')}</code>)\n"
            f"💳 Karta: <code>{p.get('card_number')}</code>\n"
            f"📅 {p.get('created_at')}"
        )
        receipt = p.get("receipt_path")
        if receipt and Path(receipt).is_file():
            await message.answer_photo(
                FSInputFile(receipt),
                caption=text,
                reply_markup=payment_review_kb(pid),
            )
        else:
            await message.answer(text, reply_markup=payment_review_kb(pid))


@router.message(F.text == ADMIN_BTN_FILES)
async def admin_files(message: Message) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
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


@router.callback_query(F.data.startswith("pay_approve_") | F.data.startswith("pay_reject_"))
async def payment_callback(query: CallbackQuery) -> None:
    if not query.from_user or not _is_admin(query.from_user.id):
        await query.answer("Faqat admin.", show_alert=True)
        return

    await query.answer("⏳")

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
        result = payment_service.approve_payment(pid)
        if result:
            tid = int(result["telegram_id"])
            credits = users_repo.get_credits(tid)
            await _update_payment_review_message(
                query.message,
                f"✅ To'lov #{pid} tasdiqlandi.\n"
                f"Foydalanuvchi krediti: {credits}",
            )
            await query.bot.send_message(
                tid,
                f"✅ To'lovingiz tasdiqlandi!\n"
                f"💳 Kredit: <b>{credits}</b> ta\n"
                f"ℹ️ 1 kredit = 1 hujjat (CV <b>yoki</b> Obyektivka).",
            )
        elif query.message:
            await query.message.reply("Tasdiqlash xatosi.")
    else:
        ok = payment_service.reject_payment(pid)
        if ok:
            payment = payments_repo.get_payment(pid)
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
