from telegram import Update
from telegram.ext import ContextTypes
from bot.keyboards.reply_keyboards import get_back_button

async def premium_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle premium services"""
    premium_text = (
        "💎 **Premium Xizmatlar**\n\n"
        "🚀 Kengaytirilgan imkoniyatlar:\n\n"
        "• **Obyektivka AI Pro** - Kengaytirilgan shablon va AI\n"
        "• **Rasm → Word Pro** - Yuqori aniqlik va ko'p til\n"
        "• **Modern CV Builder** - Professional CV dizayner\n"
        "• **Qo'shimcha xizmatlar** - Tez orada...\n\n"
        "💰 **Narxlar:**\n"
        "• Oylik: 50,000 so'm\n"
        "• 3 oylik: 120,000 so'm\n"
        "• 6 oylik: 220,000 so'm\n\n"
        "Faollashtirish uchun admin bilan bog'laning: @admin"
    )
    
    await update.message.reply_text(
        premium_text,
        reply_markup=get_back_button(),
        parse_mode="Markdown"
    )
