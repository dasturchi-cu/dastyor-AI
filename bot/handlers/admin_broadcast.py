"""Admin: hammaga xabar yuborish + hisobot."""
from __future__ import annotations

import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.services.admin_service import is_admin
from bot.services.broadcast_service import (
    collect_broadcast_recipients,
    format_broadcast_report,
    run_broadcast,
)
from bot.ui.messages import BROADCAST_FIX_ANNOUNCEMENT
from bot.ui.keyboards import (
    ADMIN_BTN_BROADCAST,
    ADMIN_BTN_BROADCAST_CANCEL,
    admin_menu,
)

logger = logging.getLogger(__name__)

_STEP = "admin_broadcast_step"
_DRAFT = "admin_broadcast_draft"


def _confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Yuborish", callback_data="broadcast_confirm"),
                InlineKeyboardButton("❌ Bekor", callback_data="broadcast_cancel"),
            ],
        ]
    )


async def start_broadcast_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Faqat adminlar uchun.")
        return
    n = len(collect_broadcast_recipients())
    context.user_data[_STEP] = "await_text"
    context.user_data.pop(_DRAFT, None)
    await update.message.reply_text(
        "📢 <b>Hammaga xabar</b>\n\n"
        f"👥 Ro‘yxat: <b>{n}</b> ta foydalanuvchi.\n\n"
        "E’lon matnini yuboring.\n"
        "Tayyor xabar: /broadcast tayyor\n"
        f"Bekor: {ADMIN_BTN_BROADCAST_CANCEL}",
        parse_mode="HTML",
        reply_markup=admin_menu(),
    )


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Faqat adminlar uchun.")
        return
    args = (context.args or [])
    if args and args[0].lower() in ("tayyor", "ready", "fix"):
        context.user_data[_DRAFT] = BROADCAST_FIX_ANNOUNCEMENT
        context.user_data[_STEP] = "confirm"
        await _send_preview(update, context)
        return
    await start_broadcast_flow(update, context)


async def _send_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message or (update.callback_query.message if update.callback_query else None)
    if not msg:
        return
    draft = (context.user_data.get(_DRAFT) or "").strip()
    if not draft:
        await msg.reply_text("⚠️ Matn bo‘sh.")
        return
    n = len(collect_broadcast_recipients())
    preview = draft if len(draft) <= 900 else draft[:900] + "…"
    await msg.reply_text(
        "👀 <b>Ko‘rib chiqing</b>\n\n" + preview + f"\n\n👥 <b>{n}</b> kishiga yuboriladi. Tasdiqlaysizmi?",
        parse_mode="HTML",
        reply_markup=_confirm_keyboard(),
    )


async def handle_admin_broadcast_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """True = xabar qayta ishlandi."""
    if not update.message or not update.effective_user:
        return False
    if not is_admin(update.effective_user.id):
        return False
    step = context.user_data.get(_STEP)
    if not step:
        return False

    text = (update.message.text or "").strip()
    if text == ADMIN_BTN_BROADCAST_CANCEL:
        context.user_data.pop(_STEP, None)
        context.user_data.pop(_DRAFT, None)
        await update.message.reply_text("↩️ Yuborish bekor qilindi.", reply_markup=admin_menu())
        return True

    if step == "await_text":
        if not text:
            await update.message.reply_text("⚠️ Matn yuboring.")
            return True
        if text == ADMIN_BTN_BROADCAST:
            await start_broadcast_flow(update, context)
            return True
        context.user_data[_DRAFT] = text
        context.user_data[_STEP] = "confirm"
        await _send_preview(update, context)
        return True

    return False


async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user or not is_admin(q.from_user.id):
        if q:
            await q.answer("Faqat admin.", show_alert=True)
        return
    await q.answer()
    data = (q.data or "").strip()
    msg = q.message

    if data == "broadcast_cancel":
        context.user_data.pop(_STEP, None)
        context.user_data.pop(_DRAFT, None)
        if msg:
            await msg.edit_text("↩️ Yuborish bekor qilindi.")
        return

    if data != "broadcast_confirm":
        return

    draft = (context.user_data.get(_DRAFT) or "").strip()
    if not draft:
        await q.answer("Matn yo‘q.", show_alert=True)
        return

    context.user_data.pop(_STEP, None)
    context.user_data.pop(_DRAFT, None)
    admin_chat = q.from_user.id
    if msg:
        await msg.edit_text(
            "⏳ <b>Yuborilmoqda…</b>\nBir necha daqiqa olishi mumkin. Hisobot shu yerga keladi.",
            parse_mode="HTML",
        )

    async def _job():
        try:
            result = await run_broadcast(
                context.bot,
                draft,
                parse_mode="HTML",
                progress_chat_id=admin_chat,
            )
            report = format_broadcast_report(result)
            await context.bot.send_message(
                chat_id=admin_chat,
                text=report,
                parse_mode="HTML",
                reply_markup=admin_menu(),
            )
        except Exception as e:
            logger.exception("broadcast failed: %s", e)
            await context.bot.send_message(
                chat_id=admin_chat,
                text=f"❌ Yuborish xatosi: {str(e)[:300]}",
                reply_markup=admin_menu(),
            )

    asyncio.create_task(_job())
