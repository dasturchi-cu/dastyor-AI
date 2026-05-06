"""Minimal Telegram bot for CV/Obyektivka, support, and admin payment alerts."""
from __future__ import annotations

import logging
import os

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    WebAppInfo,
)
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.handlers.feedback import handle_feedback, start_feedback
from bot.ui.messages import HELP_TEXT, WELCOME_TEXT

try:
    from bot.handlers.premium import premium_payment_review_callback
except Exception:  # premium module may be removed in minimal build
    async def premium_payment_review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.callback_query:
            await update.callback_query.answer("Payment review handler o'chirilgan.", show_alert=False)

logger = logging.getLogger(__name__)
BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip()
WEBAPP_BASE = (os.getenv("WEBAPP_BASE") or "").strip().rstrip("/")
SUPPORT_GROUP_ID = int((os.getenv("SUPPORT_GROUP_ID") or "-1003457224552").strip())
_ADMIN_IDS = {
    int(v.strip())
    for v in (os.getenv("ADMIN_USER_ID") or "").split(",")
    if v.strip().isdigit()
}

BTN_CV = "📄 CV Resume"
BTN_OBY = "✍️ Obyektivka"
BTN_CONTACT = "🆘 Murojaat"
BTN_HELP = "ℹ️ Yordam"

ADMIN_BTN_STATS = "📊 Holat"
ADMIN_BTN_SUPPORT = "📨 Murojaatlar"
ADMIN_BTN_PAYMENTS = "💳 To'lovlar"
ADMIN_BTN_CLOSE = "🚪 Yopish"


def _menu_markup(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("CV", web_app=WebAppInfo(url=f"{WEBAPP_BASE}/cv.html?telegram_id={uid}"))],
            [InlineKeyboardButton("Obyektivka", web_app=WebAppInfo(url=f"{WEBAPP_BASE}/obyektivka.html?telegram_id={uid}"))],
        ]
    )


def _reply_menu(uid: int) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text=BTN_CV,
                    web_app=WebAppInfo(url=f"{WEBAPP_BASE}/cv.html?telegram_id={uid}"),
                ),
                KeyboardButton(
                    text=BTN_OBY,
                    web_app=WebAppInfo(url=f"{WEBAPP_BASE}/obyektivka.html?telegram_id={uid}"),
                ),
            ],
            [KeyboardButton(BTN_CONTACT), KeyboardButton(BTN_HELP)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Xizmatni tanlang...",
    )


def _admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(ADMIN_BTN_STATS), KeyboardButton(ADMIN_BTN_SUPPORT)],
            [KeyboardButton(ADMIN_BTN_PAYMENTS), KeyboardButton(ADMIN_BTN_CLOSE)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Admin bo'limi",
    )


def _is_admin(update: Update) -> bool:
    uid = int(update.effective_user.id) if update.effective_user else 0
    return uid in _ADMIN_IDS


async def _send_with_typing(update: Update, text: str, *, reply_markup=None) -> None:
    if not update.effective_chat or not update.message:
        return
    await update.get_bot().send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await update.message.reply_text(text, reply_markup=reply_markup)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if (
        not update.effective_user
        or not update.effective_chat
        or update.effective_chat.type != "private"
        or not update.message
    ):
        return
    uid = int(update.effective_user.id)
    # Remove any old legacy reply keyboard from previous bot versions.
    await update.message.reply_text("Yangi menyu yuklandi.", reply_markup=ReplyKeyboardRemove())
    await _send_with_typing(
        update,
        WELCOME_TEXT,
        reply_markup=_reply_menu(uid),
    )
    await update.message.reply_text("Tez ochish:", reply_markup=_menu_markup(uid))


async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_feedback(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    uid = int(update.effective_user.id)
    await _send_with_typing(
        update,
        HELP_TEXT,
        reply_markup=_reply_menu(uid),
    )


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    if not _is_admin(update):
        await update.message.reply_text("Bu bo'lim faqat adminlar uchun.")
        return
    await _send_with_typing(update, "Admin panel ochildi.", reply_markup=_admin_menu())


async def admin_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not _is_admin(update):
        return
    txt = (update.message.text or "").strip()
    if txt == ADMIN_BTN_STATS:
        await _send_with_typing(update, "✅ Bot ishlayapti. Holat: barqaror.")
    elif txt == ADMIN_BTN_SUPPORT:
        await _send_with_typing(
            update,
            f"📨 Murojaatlar guruhi: {SUPPORT_GROUP_ID}\nYangi murojaatlar shu yerga yuboriladi.",
        )
    elif txt == ADMIN_BTN_PAYMENTS:
        await _send_with_typing(update, "💳 To'lov bildirishnomalari admin guruhga yuboriladi.")
    elif txt == ADMIN_BTN_CLOSE:
        await update.message.reply_text("Admin panel yopildi.", reply_markup=ReplyKeyboardRemove())


async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user or not update.effective_chat:
        return

    if context.user_data.get("waiting_for") == "feedback":
        await handle_feedback(update, context)
        return

    text = (update.message.text or "").strip()
    uid = int(update.effective_user.id)

    if text == BTN_CV or text == BTN_OBY:
        await update.message.reply_text("Xizmatni ochish uchun tugmani bir marta bosing.", reply_markup=_reply_menu(uid))
        return
    if text == BTN_CONTACT:
        await start_feedback(update, context)
        return
    if text == BTN_HELP:
        await help_command(update, context)
        return
    if text.lower() in {"bekor", "cancel", "orqaga", "ortga"}:
        await update.message.reply_text("↩️ Asosiy menyuga qaytdik.", reply_markup=_reply_menu(uid))
        return
    await admin_text_router(update, context)


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
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("contact", support_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(premium_payment_review_callback, pattern=r"^prempay_(approve|reject)_\d+$"))
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
