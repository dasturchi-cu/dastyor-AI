import asyncio

from telegram import Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

import bot.services.user_service as crm
from bot.services.admin_service import is_admin as is_admin_sync
from bot.services.settings_service import get_maintenance_mode


def _track_user_activity_job(user, cmd: str | None, dm_chat_id: int | None) -> None:
    """Supabase/JSON CRM — event loopni bloklamaslik uchun alohida thread."""
    crm.track_user_activity(user, command=cmd, chat_id=dm_chat_id)


async def track_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Middleware: ban tekshiruvi + CRM (fon-da, javobni sekinlatmaydi)."""
    if update.effective_user:
        uid = update.effective_user.id
        # Enrich Sentry scope for bot errors (who/what update)
        try:
            import sentry_sdk

            with sentry_sdk.configure_scope() as scope:
                scope.set_user({"id": int(uid), "username": update.effective_user.username})
                scope.set_tag("tg.update_type", type(update).__name__)
                if update.effective_chat:
                    scope.set_tag("tg.chat_type", getattr(update.effective_chat, "type", None))
        except Exception:
            pass
        # Global maintenance mode: block EVERYTHING for non-admins (bot-wide).
        # This runs before all handlers (group=-1 TypeHandler in main.py).
        try:
            if get_maintenance_mode() and not is_admin_sync(uid):
                context.user_data["maintenance_blocked"] = True
                # Reply only in private chats to avoid spam in groups.
                try:
                    if update.effective_chat and update.effective_chat.type == "private":
                        last = float(context.user_data.get("_maint_last_ts") or 0)
                        now = __import__("time").time()
                        # simple anti-spam: max 1 reply per 20s per user
                        if now - last > 20:
                            context.user_data["_maint_last_ts"] = now
                            if update.message:
                                await update.message.reply_text(
                                    "🛠 Botda texnik ishlar ketmoqda. Iltimos, birozdan keyin qayta urinib ko‘ring."
                                )
                            elif update.callback_query:
                                try:
                                    await update.callback_query.answer(
                                        "🛠 Texnik ishlar. Keyinroq urinib ko‘ring.",
                                        show_alert=True,
                                    )
                                except Exception:
                                    pass
                except Exception:
                    pass
                # Hard-stop remaining handlers (commands, callbacks, message routers)
                raise ApplicationHandlerStop
        except Exception:
            # fail open: do not block if settings read fails
            pass
        # get_user_profile ichida qisqa TTL kesh — har xabarga thread kerak emas.
        banned = crm.is_user_banned(uid)
        if banned:
            if not is_admin_sync(uid):
                context.user_data["is_banned"] = True
                raise ApplicationHandlerStop

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
