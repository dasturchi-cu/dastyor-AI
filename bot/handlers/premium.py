import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.keyboards.reply_keyboards import get_back_button
from bot.services.settings_service import get_premium_status, get_premium_expiry

CARD_NUMBER = "9860 1201 7225 8424"
CARD_OWNER = "DILNOZA MOMINOVA"
PREMIUM_ADMIN_GROUP_ID = int(os.getenv("PREMIUM_ADMIN_GROUP_ID", "-1003457224552"))

PLAN_INFO = {
    "standard": {"title": "Standard", "days": 7},
    "premium": {"title": "Premium", "days": 30},
}


def _premium_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📋 Kartani nusxa olish", callback_data="buy_copy_card")],
        ]
    )


def _card_message(plan_title: str) -> str:
    return (
        "💎 <b>Premium sotib olish</b>\n\n"
        "Premium olish uchun quyidagi kartaga to‘lov qiling.\n\n"
        "💳 <b>Karta raqami:</b>\n"
        f"<code>{CARD_NUMBER}</code>\n\n"
        "👤 <b>Karta egasi:</b>\n"
        f"<b>{CARD_OWNER}</b>\n\n"
        "To‘lov qilgandan keyin skrenshotni shu chatga yuboring.\n\n"
        f"📦 Tarif: <b>{plan_title}</b>"
    )


async def premium_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Premium purchase entry point (private chat only)."""
    if not update.effective_chat or update.effective_chat.type != "private":
        return

    uid = update.effective_user.id if update.effective_user else None
    status_line = ""
    if uid:
        st = get_premium_status(uid)
        if st == "active":
            exp = get_premium_expiry(uid) or "-"
            status_line = f"\n\n✅ Sizda faol premium bor. Tugash sanasi: <b>{exp}</b>"
        elif st == "expired":
            status_line = "\n\n⚠️ Premium muddati tugagan. Yangilash mumkin."

    # Default plan unless user selects otherwise elsewhere
    context.user_data["premium_plan"] = context.user_data.get("premium_plan") or "premium"
    context.user_data["waiting_for"] = "premium_payment_screenshot"
    plan_data = PLAN_INFO.get(str(context.user_data.get("premium_plan")).lower(), PLAN_INFO["premium"])
    await update.message.reply_text(
        _card_message(plan_data["title"]),
        parse_mode="HTML",
        reply_markup=_premium_keyboard(),
    )
    if status_line:
        await update.message.reply_text(status_line, parse_mode="HTML", reply_markup=get_back_button())


async def premium_purchase_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline actions for premium purchase card."""
    query = update.callback_query
    if not query:
        return
    await query.answer()

    if not query.message or not query.message.chat or query.message.chat.type != "private":
        return

    data = query.data or ""
    if data == "buy_copy_card":
        # Send plain card number to chat so user can copy easily
        try:
            await query.message.reply_text(CARD_NUMBER)
        except Exception:
            pass
        return

    return


async def handle_premium_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Accept payment screenshot in private chat and forward to admin group.
    Returns True if update was handled.
    """
    if not update.message or not update.effective_user:
        return False
    if not update.effective_chat or update.effective_chat.type != "private":
        return False
    if context.user_data.get("waiting_for") != "premium_payment_screenshot":
        return False

    has_media = bool(update.message.photo or update.message.document)
    if not has_media:
        await update.message.reply_text("❌ Iltimos, to'lov skrenshotini rasm yoki fayl ko'rinishida yuboring.")
        return True

    plan = str(context.user_data.get("premium_plan", "premium")).lower()
    plan_data = PLAN_INFO.get(plan, PLAN_INFO["premium"])
    user = update.effective_user
    uname = f"@{user.username}" if user.username else "yo'q"
    caption = (
        "💰 <b>Yangi premium to‘lov</b>\n\n"
        f"User: {uname}\n"
        f"ID: <code>{user.id}</code>\n"
        f"Tarif: <b>{plan_data['title']}</b>\n\n"
        f"Tasdiqlash: <code>/approve {user.id}</code>"
    )

    try:
        if update.message.photo:
            await context.bot.send_photo(
                chat_id=PREMIUM_ADMIN_GROUP_ID,
                photo=update.message.photo[-1].file_id,
                caption=caption,
                parse_mode="HTML",
            )
        else:
            await context.bot.send_document(
                chat_id=PREMIUM_ADMIN_GROUP_ID,
                document=update.message.document.file_id,
                caption=caption,
                parse_mode="HTML",
            )
    except Exception:
        await update.message.reply_text("❌ Fayl yuborishda xatolik yuz berdi")
        return True

    context.user_data.pop("waiting_for", None)
    await update.message.reply_text(
        "✅ Skrenshot qabul qilindi. Admin tasdiqlaganidan keyin premium faollashadi."
    )
    return True
