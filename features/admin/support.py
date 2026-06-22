"""Support chat — relay user messages to support group and admins."""
from __future__ import annotations

import html
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config.settings import settings
from database.repositories import support_messages as support_repo
from database.repositories import users as users_repo
from features.admin.keyboards import support_reply_kb
from features.bot.states import ContactStates
from shared.keyboards import is_admin_menu_button, is_menu_button
from shared.payment_notifications import format_username

logger = logging.getLogger(__name__)
router = Router()

_ACK = "✅ Murojaatingiz qabul qilindi. Tez orada javob beramiz."


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_user_ids


def _support_header(message: Message) -> str:
    user = message.from_user
    if not user:
        return ""
    tid = user.id
    users_repo.upsert_user(
        tid,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )
    name = html.escape(
        " ".join(filter(None, [user.first_name, user.last_name])).strip() or "—"
    )
    username = html.escape(format_username(user.username))
    return (
        f"<b>📩 Murojaat</b>\n\n"
        f"User ID: <code>{tid}</code>\n"
        f"Username: {username}\n"
        f"Name: <a href=\"tg://user?id={tid}\">{name}</a>"
    )


async def _send_relay_payload(
    message: Message,
    chat_id: int,
    *,
    with_reply_kb: bool = False,
) -> None:
    header = _support_header(message)
    kb = support_reply_kb(message.from_user.id) if with_reply_kb else None
    await message.bot.send_message(chat_id, header, reply_markup=kb)
    if message.text:
        await message.bot.send_message(
            chat_id,
            f"<i>Xabar:</i>\n{html.escape(message.text)}",
        )
    else:
        await message.copy_to(chat_id)


async def relay_user_message_to_support(message: Message) -> bool:
    """Forward a user message to the support group and admin DMs."""
    if not message.from_user:
        return False

    preview = (message.text or message.caption or "[media]").strip()[:500]
    group_id = settings.support_group_id
    admin_ids = settings.admin_user_ids
    if not group_id and not admin_ids:
        return False

    support_repo.create_message(message.from_user.id, preview)
    delivered = False

    if group_id:
        try:
            await _send_relay_payload(message, group_id, with_reply_kb=True)
            delivered = True
        except Exception as exc:
            logger.warning("Support relay to group failed: %s", exc)

    for admin_id in admin_ids:
        if admin_id == message.from_user.id:
            continue
        try:
            await _send_relay_payload(message, admin_id)
            delivered = True
        except Exception as exc:
            logger.warning("Support relay to admin %s failed: %s", admin_id, exc)

    return delivered


@router.message(ContactStates.waiting_message)
async def relay_contact_mode(message: Message, state: FSMContext) -> None:
    if not message.from_user or _is_admin(message.from_user.id):
        return
    if users_repo.is_blocked(message.from_user.id):
        await message.answer("⛔ Siz bloklangansiz. Murojaat qabul qilinmaydi.")
        return
    if message.text:
        if message.text.startswith("/"):
            return
        if is_menu_button(message.text) or is_admin_menu_button(message.text):
            return

    if await relay_user_message_to_support(message):
        await message.answer(_ACK)
    else:
        await message.answer(
            "❌ Hozircha murojaat yuborib bo'lmadi. "
            f"Iltimos, @{settings.support_admin_username} ga to'g'ridan-to'g'ri yozing."
        )


@router.message(F.chat.type == "private")
async def relay_private_to_support(message: Message, state: FSMContext) -> None:
    if not message.from_user or _is_admin(message.from_user.id):
        return
    if await state.get_state():
        return
    if users_repo.is_blocked(message.from_user.id):
        await message.answer("⛔ Siz bloklangansiz. Murojaat qabul qilinmaydi.")
        return
    if message.text:
        if message.text.startswith("/"):
            return
        if is_menu_button(message.text) or is_admin_menu_button(message.text):
            return

    if await relay_user_message_to_support(message):
        await message.answer(_ACK)
