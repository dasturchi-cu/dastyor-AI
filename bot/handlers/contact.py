from telegram import Update
from telegram.ext import ContextTypes
from bot.keyboards.reply_keyboards import get_back_button

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show contact information"""
    contact_text = (
        "✉️ **Aloqa uchun**\n\n"
        "📞 **Support:**\n"
        "• Telegram: @lashbot_support\n"
        "• Admin: @lashbot_admin\n\n"
        "⏰ **Ish vaqti:**\n"
        "Dushanba-Shanba: 09:00-18:00\n\n"
        "💬 **Murojaat yuborish:**\n"
        "Muammolaringizni yoki takliflaringizni bizga yozishingiz mumkin."
    )
    
    await update.message.reply_text(
        contact_text,
        reply_markup=get_back_button(),
        parse_mode="Markdown"
    )
