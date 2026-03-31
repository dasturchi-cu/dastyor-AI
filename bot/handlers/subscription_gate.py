import logging
import os
from typing import Iterable

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatMemberStatus
from telegram.ext import ApplicationHandlerStop, CallbackQueryHandler, ContextTypes

from bot.services.admin_service import is_admin

logger = logging.getLogger(__name__)


_DEFAULT_CHANNELS = [
    "@Andijon_Asaka_ish",
    "@asaka",
    "@andijon_ish_bor_kerak_elonlar",
    "@SHAHRIXON_ISH_BOR_ELON",
]


def _required_channels() -> list[str]:
    raw = (os.getenv("REQUIRED_CHANNELS") or "").strip()
    if not raw:
        return list(_DEFAULT_CHANNELS)
    out: list[str] = []
    for c in raw.split(","):
        c = (c or "").strip()
        if not c:
            continue
        if not c.startswith("@") and "t.me/" not in c:
            c = "@" + c
        if "t.me/" in c:
            c = c.split("t.me/", 1)[-1].strip()
            if not c.startswith("@"):
                c = "@" + c
        out.append(c)
    return out or list(_DEFAULT_CHANNELS)


def _channel_url(ch: str) -> str:
    name = (ch or "").strip()
    if name.startswith("@"):
        name = name[1:]
    return f"https://t.me/{name}"


def _not_subscribed_kb(channels: Iterable[str]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(c, url=_channel_url(c))] for c in channels]
    rows.append([InlineKeyboardButton("✅ Tekshirish", callback_data="subcheck")])
    return InlineKeyboardMarkup(rows)


async def _is_subscribed_to_all(bot, user_id: int, channels: list[str]) -> bool:
    for ch in channels:
        try:
            m = await bot.get_chat_member(chat_id=ch, user_id=int(user_id))
            st = getattr(m, "status", None)
            if st in (
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.OWNER,
                "member",
                "administrator",
                "creator",
            ):
                continue
            return False
        except Exception as e:
            logger.info("subscription check failed ch=%s user=%s err=%s", ch, user_id, e)
            return False
    return True


async def enforce_subscription_or_block(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Global gate: before any action, user must be subscribed to all required channels.
    Blocks handlers using ApplicationHandlerStop.
    """
    if not update.effective_user or not update.effective_chat:
        return
    if update.effective_chat.type != "private":
        return
    uid = int(update.effective_user.id)
    if is_admin(uid):
        return
    channels = _required_channels()
    ok = await _is_subscribed_to_all(context.bot, uid, channels)
    if ok:
        # persist to DB (optional; do not block on failure)
        try:
            from bot.services.supabase_db import has_db, db_set_subscription_status
            from bot.services.user_service import invalidate_user_profile_cache

            if has_db():
                db_set_subscription_status(uid, is_subscribed=True)
                invalidate_user_profile_cache(uid)
        except Exception:
            pass
        return

    text = "❗ Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling"
    kb = _not_subscribed_kb(channels)
    try:
        if update.callback_query:
            try:
                await update.callback_query.answer()
            except Exception:
                pass
            try:
                await update.callback_query.message.reply_text(text, reply_markup=kb)
            except Exception:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=kb)
        elif update.message:
            await update.message.reply_text(text, reply_markup=kb)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=kb)
    except Exception:
        pass
    raise ApplicationHandlerStop


async def subscription_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback for ✅ Tekshirish button."""
    if not update.callback_query:
        return
    await update.callback_query.answer()
    await enforce_subscription_or_block(update, context)

    # If passed, show bonus info (once-per-user, enforced in DB on CV attempt)
    try:
        uid = int(update.effective_user.id) if update.effective_user else 0
        if uid:
            from bot.services.supabase_db import has_db, db_get_subscription_and_bonus

            if has_db():
                flags = db_get_subscription_and_bonus(uid) or {}
                if not bool(flags.get("bonus_used", False)):
                    await update.callback_query.message.reply_text(
                        "🎁 Siz 1 marta bepul CV yuklab olish bonusiga ega bo‘ldingiz."
                    )
    except Exception:
        pass


def handler() -> CallbackQueryHandler:
    return CallbackQueryHandler(subscription_check_callback, pattern=r"^subcheck$")

