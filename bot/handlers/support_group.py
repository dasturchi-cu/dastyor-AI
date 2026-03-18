import os
import re
from telegram import Update
from telegram.ext import ContextTypes

from bot.services.admin_service import is_admin
from bot.services.support_service import create_support_request


SUPPORT_GROUP_ID = int(os.getenv("SUPPORT_GROUP_ID", "-1003457224552"))


def _extract_target_user_id_from_message(message) -> int | None:
    """
    Parse target user id from support forwarded header text/caption.
    Expected patterns include:
    - "ID: <code>12345</code>"
    - "ID: 12345"
    - "🆔 User ID: <code>12345</code>"
    """
    raw = ""
    if message:
        raw = (message.caption or "") + "\n" + (message.text or "")
    if not raw:
        return None
    m = re.search(r"(?:User ID|ID)\s*:\s*(?:<code>)?(\d{5,})(?:</code>)?", raw, flags=re.IGNORECASE)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


async def support_group_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Restrict support-group behavior:
    - normal users: complaints/screenshots only
    - admins: reply to forwarded ticket -> forward answer to user
    - ignore all commands and unrelated messages
    """
    msg = update.message
    chat = update.effective_chat
    user = update.effective_user
    if not msg or not chat or not user:
        return
    if chat.id != SUPPORT_GROUP_ID:
        return

    # Ignore any bot command in support group.
    if msg.text and msg.text.startswith("/"):
        return

    user_is_admin = is_admin(user.id)

    # Admin reply flow (replying to forwarded complaint header).
    if user_is_admin and msg.reply_to_message and (msg.text or msg.caption):
        target_uid = _extract_target_user_id_from_message(msg.reply_to_message)
        if target_uid:
            reply_text = (msg.text or msg.caption or "").strip()
            if reply_text:
                try:
                    await context.bot.send_message(
                        chat_id=target_uid,
                        text=f"📩 Admin javobi:\n\n{reply_text}",
                    )
                except Exception:
                    pass
        return

    # Non-admin users: complaints/screenshots
    if not user_is_admin:
        if msg.text or msg.photo or msg.document:
            create_support_request(
                user_id=user.id,
                username=user.username or "",
                message=(msg.text or msg.caption or "[Support attachment]").strip(),
                source="support_group",
            )
            return

    # Everything else in support group is ignored.
    return

