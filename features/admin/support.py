"""Support chat — relay user messages to support group."""
from __future__ import annotations

import html
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config.settings import settings
from database.repositories import users as users_repo
from features.admin.keyboards import support_reply_kb
from shared.keyboards import is_admin_menu_button, is_menu_button
from shared.payment_notifications import format_username

logger = logging.getLogger(__name__)
router = Router()


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

    group_id = settings.support_group_id
    if not group_id:
        return

    header = _support_header(message)
    kb = support_reply_kb(message.from_user.id)
    try:
        await message.bot.send_message(group_id, header, reply_markup=kb)
        if message.text:
            await message.bot.send_message(
                group_id,
                f"<i>Xabar:</i>\n{html.escape(message.text)}",
            )
        else:
            await message.copy_to(group_id)
        await message.answer(
            "✅ Murojaatingiz qabul qilindi. Tez orada javob beramiz."
        )
    except Exception as exc:
        logger.warning("Support relay failed: %s", exc)
