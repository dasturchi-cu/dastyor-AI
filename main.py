"""Minimal Telegram bot for CV/Obyektivka, support, and admin payment alerts."""
from __future__ import annotations

import asyncio
import logging
import os
import time

from dotenv import load_dotenv
from telegram import ReplyKeyboardRemove, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.constants.states import WaitingState
from bot.flow.state import WAITING_FOR_FEEDBACK
from bot.handlers.feedback import handle_feedback, start_feedback
from bot.handlers.my_documents import (
    docs_command,
    handle_my_docs_button,
    is_my_docs_button,
)
from bot.handlers.obyektivka import handle_obyektivka_audio
from bot.handlers.service_intro import (
    handle_cv_intro,
    handle_menu_back,
    handle_obyektivka_intro,
    intro_callback_router,
    is_cv_button,
    is_oby_button,
)
from bot.ui.keyboards import cv_button_labels, oby_button_labels
from bot.ui.keyboards import (
    ADMIN_BTN_CLOSE,
    ADMIN_BTN_DIGEST,
    ADMIN_BTN_PAYMENTS,
    ADMIN_BTN_STATS,
    ADMIN_BTN_SUPPORT,
    BTN_BACK,
    BTN_CONTACT,
    BTN_HELP,
    BTN_MY_DOCS,
    user_reply_menu,
    admin_menu,
)
from bot.ui.messages import (
    ADMIN_ONLY_TEXT,
    ADMIN_PANEL_OPENED_TEXT,
    HELP_TEXT,
    OBY_AUDIO_WAIT_HINT,
    UNKNOWN_INPUT_TEXT,
    WELCOME_TEXT,
)

try:
    from bot.handlers.premium import premium_payment_review_callback
except Exception:  # premium module may be removed in minimal build
    async def premium_payment_review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.callback_query:
            await update.callback_query.answer("Payment review handler o'chirilgan.", show_alert=False)

logger = logging.getLogger(__name__)
load_dotenv(override=True)
# Some editors save .env with UTF-8 BOM; support both keys safely.
BOT_TOKEN = (os.getenv("BOT_TOKEN") or os.getenv("\ufeffBOT_TOKEN") or "").strip()
from config import WEBAPP_BASE, resolve_webapp_base
SUPPORT_GROUP_ID = int((os.getenv("SUPPORT_GROUP_ID") or "-1003457224552").strip())
PREMIUM_ADMIN_GROUP_ID = int((os.getenv("PREMIUM_ADMIN_GROUP_ID") or str(SUPPORT_GROUP_ID)).strip())
_ADMIN_IDS = {
    int(v.strip())
    for v in (os.getenv("ADMIN_USER_ID") or "").split(",")
    if v.strip().isdigit()
}

LAST_ACTION_TS = "_last_action_ts"


def _is_admin(update: Update) -> bool:
    uid = int(update.effective_user.id) if update.effective_user else 0
    return uid in _ADMIN_IDS


async def _send_with_typing(update: Update, text: str, *, reply_markup=None, parse_mode: str | None = None) -> None:
    if not update.effective_chat or not update.message:
        return
    await update.get_bot().send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)


def _is_fast_repeat(context: ContextTypes.DEFAULT_TYPE, min_gap_seconds: float = 0.35) -> bool:
    now = time.monotonic()
    prev = float(context.user_data.get(LAST_ACTION_TS, 0.0) or 0.0)
    context.user_data[LAST_ACTION_TS] = now
    return (now - prev) < min_gap_seconds


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if (
        not update.effective_user
        or not update.effective_chat
        or update.effective_chat.type != "private"
        or not update.message
    ):
        return
    uid = int(update.effective_user.id)
    context.user_data.pop("waiting_for", None)
    try:
        from bot.services.user_service import track_user_activity

        await asyncio.to_thread(
            track_user_activity,
            update.effective_user,
            "start",
            update.effective_chat.id,
        )
    except Exception:
        pass
    try:
        from bot.services.bot_analytics import log_bot_event

        asyncio.create_task(asyncio.to_thread(log_bot_event, uid, "bot_start"))
    except Exception:
        pass
    try:
        await update.message.reply_text(
            WELCOME_TEXT,
            reply_markup=user_reply_menu(WEBAPP_BASE, uid),
            parse_mode="HTML",
        )
    except Exception:
        await _send_with_typing(
            update,
            WELCOME_TEXT,
            reply_markup=user_reply_menu(WEBAPP_BASE, uid),
            parse_mode="HTML",
        )


async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_feedback(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    uid = int(update.effective_user.id)
    await _send_with_typing(
        update,
        HELP_TEXT,
        reply_markup=user_reply_menu(WEBAPP_BASE, uid),
        parse_mode="HTML",
    )


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    if not _is_admin(update):
        await update.message.reply_text(ADMIN_ONLY_TEXT)
        return
    await _send_with_typing(update, ADMIN_PANEL_OPENED_TEXT, reply_markup=admin_menu())


async def admin_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not _is_admin(update):
        return
    txt = (update.message.text or "").strip()
    if txt == ADMIN_BTN_STATS:
        from bot.services.bot_admin_stats import format_admin_stats_text

        await _send_with_typing(update, format_admin_stats_text(), parse_mode="HTML")
    elif txt == ADMIN_BTN_DIGEST:
        from bot.services.bot_admin_stats import send_daily_admin_digest

        await send_daily_admin_digest(update.get_bot(), PREMIUM_ADMIN_GROUP_ID)
        await update.message.reply_text("📋 Kunlik hisobot admin guruhiga yuborildi.")
    elif txt == ADMIN_BTN_SUPPORT:
        await _send_with_typing(
            update,
            f"📨 Murojaatlar guruhi: {SUPPORT_GROUP_ID}\nYangi murojaatlar shu yerga yuboriladi.",
        )
    elif txt == ADMIN_BTN_PAYMENTS:
        await _send_with_typing(
            update,
            f"💳 To'lovlar guruhi: {PREMIUM_ADMIN_GROUP_ID}\nSkrinshotlar shu yerga tushadi.",
        )
    elif txt == ADMIN_BTN_CLOSE:
        uid = int(update.effective_user.id) if update.effective_user else 0
        await update.message.reply_text(
            "Admin panel yopildi.",
            reply_markup=user_reply_menu(WEBAPP_BASE, uid),
        )


async def cv_oby_intro_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """CV / Obyektivka — birinchi navbatda yo‘riqnoma (eski WebApp menyu ustidan)."""
    if not update.message or not update.effective_user:
        return
    text = (update.message.text or "").strip()
    context.user_data["_skip_message_router"] = True
    try:
        if is_cv_button(text):
            await handle_cv_intro(update, context)
        elif is_oby_button(text):
            await handle_obyektivka_intro(update, context)
    except Exception as e:
        logger.error("cv_oby_intro_router text=%r: %s", text[:40], e, exc_info=True)
        try:
            await update.message.reply_text(
                "❌ Xatolik. /start bosing yoki qayta urinib ko‘ring.",
            )
        except Exception:
            pass


async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user or not update.effective_chat:
        return
    if context.user_data.pop("_skip_message_router", False):
        return

    if context.user_data.get("waiting_for") == WAITING_FOR_FEEDBACK:
        await handle_feedback(update, context)
        return

    if context.user_data.get("waiting_for") == WaitingState.OBYEKTIVKA_AUDIO:
        if update.message.voice or update.message.audio:
            await handle_obyektivka_audio(update, context)
            return
        if update.message.text:
            t = (update.message.text or "").strip()
            if t == BTN_BACK or t.lower() in {"bekor", "cancel", "orqaga", "ortga"}:
                await handle_menu_back(update, context)
                return
            if is_oby_button(t):
                await handle_obyektivka_intro(update, context)
                return
            if is_my_docs_button(t):
                await handle_my_docs_button(update, context)
                return
        await update.message.reply_text(OBY_AUDIO_WAIT_HINT, parse_mode="HTML")
        return

    text = (update.message.text or "").strip()
    uid = int(update.effective_user.id)

    if text == BTN_CONTACT:
        await start_feedback(update, context)
        return
    if text == BTN_HELP:
        await help_command(update, context)
        return
    if text == BTN_MY_DOCS or is_my_docs_button(text):
        await handle_my_docs_button(update, context)
        return
    if text == BTN_BACK or text.lower() in {"bekor", "cancel", "orqaga", "ortga"}:
        await handle_menu_back(update, context)
        return
    if is_cv_button(text):
        await handle_cv_intro(update, context)
        return
    if is_oby_button(text):
        await handle_obyektivka_intro(update, context)
        return
    if _is_admin(update):
        await admin_text_router(update, context)
        return
    if _is_fast_repeat(context):
        return
    await _send_with_typing(
        update,
        UNKNOWN_INPUT_TEXT,
        reply_markup=user_reply_menu(WEBAPP_BASE, uid),
        parse_mode="HTML",
    )


def setup_application():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing.")
        return None

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connection_pool_size(int(os.getenv("PTB_POOL_SIZE", "12")))
        .pool_timeout(20.0)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", start_command))
    app.add_handler(CommandHandler("docs", docs_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("contact", support_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(premium_payment_review_callback, pattern=r"^prempay_(approve|reject)_\d+$"))
    app.add_handler(
        CallbackQueryHandler(
            intro_callback_router,
            pattern=r"^(intro_cv|intro_oby|intro_help|intro_contact|intro_my_docs|menu_back)$",
        )
    )
    class _CvObyReplyFilter(filters.MessageFilter):
        def filter(self, message):  # noqa: A003 — PTB API
            if not message or not message.text:
                return False
            return (message.text or "").strip() in (cv_button_labels() | oby_button_labels())

    cv_oby_text_filter = filters.TEXT & ~filters.COMMAND & _CvObyReplyFilter()
    app.add_handler(MessageHandler(cv_oby_text_filter, cv_oby_intro_router), group=0)
    app.add_handler(
        MessageHandler(
            (filters.TEXT & ~filters.COMMAND)
            | filters.PHOTO
            | filters.Document.ALL
            | filters.VIDEO
            | filters.VOICE
            | filters.AUDIO,
            message_router,
        ),
        group=1,
    )
    return app


async def _post_init(app) -> None:
    from bot.ui.bot_commands import sync_bot_commands

    base = resolve_webapp_base()
    app.bot_data["webapp_base"] = base
    if not base.startswith("https://"):
        logger.error("WEBAPP_BASE not https: %s — forma tugmasi ishlamaydi", base)
    else:
        logger.info("WEBAPP_BASE=%s", base)
    await sync_bot_commands(app.bot)
    if os.getenv("ADMIN_DAILY_DIGEST_ON_START", "0").strip().lower() in ("1", "true", "yes"):
        try:
            from bot.services.bot_admin_stats import send_daily_admin_digest

            await send_daily_admin_digest(app.bot, PREMIUM_ADMIN_GROUP_ID)
        except Exception as e:
            logger.warning("startup daily digest: %s", e)


async def _post_shutdown(app) -> None:
    pass


def main() -> None:
    app = setup_application()
    if app:
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
