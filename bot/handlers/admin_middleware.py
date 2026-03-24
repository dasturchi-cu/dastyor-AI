import asyncio

from telegram import Update
from telegram.ext import ContextTypes

import bot.services.user_service as crm
from bot.services.admin_service import is_admin as is_admin_sync


def _track_user_activity_job(user, cmd: str | None, dm_chat_id: int | None) -> None:
    """Supabase/JSON CRM — event loopni bloklamaslik uchun alohida thread."""
    crm.track_user_activity(user, command=cmd, chat_id=dm_chat_id)


async def track_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Middleware: ban tekshiruvi + CRM (fon-da, javobni sekinlatmaydi)."""
    if update.effective_user:
        uid = update.effective_user.id
        # get_user_profile ichida qisqa TTL kesh — har xabarga thread kerak emas.
        banned = crm.is_user_banned(uid)
        if banned:
            if not is_admin_sync(uid):
                context.user_data["is_banned"] = True
                return

        cmd = None
        if update.message and update.message.text:
            if update.message.text.startswith("/start"):
                cmd = "start"
            elif update.message.text.startswith("/"):
                cmd = "command"

        private = update.effective_chat and update.effective_chat.type == "private"
        dm_chat_id = update.effective_chat.id if private else None
        try:
            asyncio.create_task(
                asyncio.to_thread(_track_user_activity_job, update.effective_user, cmd, dm_chat_id)
            )
        except Exception:
            _track_user_activity_job(update.effective_user, cmd, dm_chat_id)
