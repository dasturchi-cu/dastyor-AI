from telegram import Update
from telegram.ext import ContextTypes
from bot.keyboards.reply_keyboards import get_back_button

async def balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user balance and top-up options"""
    user_id = update.effective_user.id
    
    # TODO: Fetch from database
    balance = 0
    credits = 0
    tariff = "Bepul"
    
    balance_text = (
        f"💰 **Balans ma'lumotlari**\n\n"
        f"👤 Foydalanuvchi ID: {user_id}\n"
        f"💵 Balans: {balance:,} so'm\n"
        f"🎟 Kreditlar: {credits}\n"
        f"📦 Tarif: {tariff}\n\n"
        "💳 **To'ldirish:**\n"
        "• Click\n"
        "• Payme\n"
        "• Uzcard\n"
        "• Humo\n\n"
        "To'ldirish uchun admin bilan bog'laning: @admin"
    )
    
    await update.message.reply_text(
        balance_text,
        reply_markup=get_back_button(),
        parse_mode="Markdown"
    )
