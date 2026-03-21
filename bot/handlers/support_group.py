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
    if user_is_admin and msg.reply_to_message:
        target_uid = _extract_target_user_id_from_message(msg.reply_to_message)
        if target_uid:
            try:
                if msg.text or msg.caption:
                    reply_text = (msg.text or msg.caption or "").strip()
                    if reply_text:
                        await context.bot.send_message(
                            chat_id=target_uid,
                            text=f"📩 Admin javobi:\n\n{reply_text}",
                        )
                elif msg.photo:
                    cap = (msg.caption or "").strip()
                    out = f"📩 Admin javobi:\n\n{cap}" if cap else "📩 Admin javobi (rasm)"
                    await context.bot.send_photo(
                        chat_id=target_uid,
                        photo=msg.photo[-1].file_id,
                        caption=out[:1024],
                    )
                elif msg.document:
                    cap = (msg.caption or "").strip()
                    out = f"📩 Admin javobi:\n\n{cap}" if cap else "📩 Admin javobi (fayl)"
                    await context.bot.send_document(
                        chat_id=target_uid,
                        document=msg.document.file_id,
                        caption=out[:1024],
                    )
            except Exception:
                pass
        return

    # Non-admin users: complaints + media (rasm, video, hujjat)
    if not user_is_admin:
        if msg.text or msg.photo or msg.document or msg.video:
            label = (
                (msg.text or msg.caption or "").strip()
                or ("[Support: video]" if msg.video else "")
                or ("[Support: rasm]" if msg.photo else "")
                or ("[Support: fayl]" if msg.document else "")
            )
            create_support_request(
                user_id=user.id,
                username=user.username or "",
                message=label,
                source="support_group",
            )
            return

    # Everything else in support group is ignored.
    return

