"""Minimal admin handlers (compatibility layer)."""
from __future__ import annotations

from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes

from bot.services.admin_service import is_admin as is_admin_sync


async def is_admin(user_id):
    return is_admin_sync(user_id)


def get_admin_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📊 Holat"), KeyboardButton("📨 Murojaatlar")],
            [KeyboardButton("💳 To'lovlar"), KeyboardButton("🚪 Yopish")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def get_admin_cancel_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("❌ Bekor qilish")]], resize_keyboard=True)


async def admin_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("Bu bo'lim faqat adminlar uchun.")
        return
    await update.message.reply_text("Admin panel ochildi.", reply_markup=get_admin_keyboard())


async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    if not await is_admin(update.effective_user.id):
        return
    txt = (update.message.text or "").strip()
    if txt == "📊 Holat":
        await update.message.reply_text("✅ Bot ishlayapti. Holat: barqaror.")
    elif txt == "📨 Murojaatlar":
        await update.message.reply_text("📨 Murojaatlar support guruhiga keladi.")
    elif txt == "💳 To'lovlar":
        await update.message.reply_text("💳 To'lovlar admin review callback orqali ko'riladi.")
    elif txt == "🚪 Yopish":
        await update.message.reply_text("Admin panel yopildi.", reply_markup=ReplyKeyboardRemove())


async def process_admin_state_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return False


# Compatibility stubs for legacy imports (kept intentionally minimal)
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_admin_text(update, context)


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from bot.handlers.admin_broadcast import broadcast_command as _broadcast

    await _broadcast(update, context)


async def add_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Bu funksiya minimal versiyada o'chirilgan.")


async def remove_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Bu funksiya minimal versiyada o'chirilgan.")


async def add_premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Premium moduli o'chirilgan.")


async def remove_premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Premium moduli o'chirilgan.")


async def approve_premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Premium moduli o'chirilgan.")


async def maintenance_on_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Maintenance komandasi minimal versiyada ishlatilmaydi.")


async def maintenance_off_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Maintenance komandasi minimal versiyada ishlatilmaydi.")


async def maintenance_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Maintenance komandasi minimal versiyada ishlatilmaydi.")


async def user_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Bu funksiya minimal versiyada o'chirilgan.")


async def top_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Bu funksiya minimal versiyada o'chirilgan.")


async def ban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Bu funksiya minimal versiyada o'chirilgan.")


async def unban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Bu funksiya minimal versiyada o'chirilgan.")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Bu funksiya minimal versiyada o'chirilgan.")


async def add_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Admin qo'shish uchun server faylida ADMIN_USER_ID yangilang.")


async def remove_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Admin o'chirish uchun server faylida ADMIN_USER_ID yangilang.")


async def support_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer("Support panel minimal versiyada o'chirilgan.", show_alert=False)
