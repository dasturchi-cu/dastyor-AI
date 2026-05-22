"""Mening hujjatlarim — /docs va tugma."""
from __future__ import annotations

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from bot.services.bot_analytics import log_bot_event
from bot.services.user_documents import format_my_documents_text
from bot.ui.keyboards import BTN_MY_DOCS, my_docs_button_labels, user_reply_menu


def is_my_docs_button(text: str) -> bool:
    return (text or "").strip() in my_docs_button_labels()


async def send_my_documents(message, context: ContextTypes.DEFAULT_TYPE, uid: int) -> None:
    try:
        await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
    except Exception:
        pass
    log_bot_event(uid, "bot_my_docs_open")
    base = context.bot_data.get("webapp_base", "")
    text = format_my_documents_text(uid)
    await message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=user_reply_menu(base, uid),
    )


async def docs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    await send_my_documents(update.message, context, int(update.effective_user.id))


async def handle_my_docs_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await send_my_documents(update.message, context, int(update.effective_user.id))
