"""Minimal Telegram bot for CV/Obyektivka, support, and admin payment alerts."""
from __future__ import annotations

import logging
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.handlers.admin import admin_panel_command, handle_admin_text
from bot.handlers.feedback import handle_feedback, start_feedback

try:
    from bot.handlers.premium import premium_payment_review_callback
except Exception:  # premium module may be removed in minimal build
    async def premium_payment_review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.callback_query:
            await update.callback_query.answer("Payment review handler o'chirilgan.", show_alert=False)

logger = logging.getLogger(__name__)
BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip()
WEBAPP_BASE = (os.getenv("WEBAPP_BASE") or "").strip().rstrip("/")


def _menu_markup(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("CV", web_app=WebAppInfo(url=f"{WEBAPP_BASE}/cv.html?telegram_id={uid}"))],
            [InlineKeyboardButton("Obyektivka", web_app=WebAppInfo(url=f"{WEBAPP_BASE}/obyektivka.html?telegram_id={uid}"))],
        ]
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.effective_chat or update.effective_chat.type != "private":
        return
    uid = int(update.effective_user.id)
    await update.message.reply_text("Assalomu alaykum. Xizmatni tanlang.", reply_markup=_menu_markup(uid))


async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_feedback(update, context)


async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("waiting_for") == "feedback":
        await handle_feedback(update, context)


def setup_application():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing.")
        return None

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connection_pool_size(int(os.getenv("PTB_POOL_SIZE", "12")))
        .pool_timeout(20.0)
        .build()
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", start_command))
    app.add_handler(CommandHandler("contact", support_command))
    app.add_handler(CommandHandler("admin", admin_panel_command))
    app.add_handler(CallbackQueryHandler(premium_payment_review_callback, pattern=r"^prempay_(approve|reject)_\d+$"))
    app.add_handler(
        MessageHandler(
            filters.Regex(r"^(📊 Statistika|📨 Xabar yuborish|📢 Kanallar|💎 Premium Boshqaruv|⚙️ Sozlamalar|👥 Foydalanuvchilar|➕ Admin qo'shish|❌ Admin o'chirish|🆘 Support so'rovlar|🚪 Panelni yopish)$"),
            handle_admin_text,
        )
    )
    app.add_handler(
        MessageHandler(
            filters.TEXT | filters.PHOTO | filters.Document.ALL | filters.VIDEO | filters.VOICE | filters.AUDIO,
            message_router,
        )
    )
    return app


def main() -> None:
    app = setup_application()
    if app:
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
