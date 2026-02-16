from telegram import Update
from telegram.ext import ContextTypes
from bot.keyboards.reply_keyboards import get_main_menu
from bot.services.user_service import get_user_profile
from bot.services.settings_service import get_daily_limit

async def balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Balans 💰' button"""
    user_id = update.effective_user.id
    profile = get_user_profile(user_id)
    limit = get_daily_limit()
    
    files = profile.get("files_processed", 0) if profile else 0
    
    # Check premium
    from bot.services.settings_service import is_premium
    has_premium = is_premium(user_id)
    
    limit_text = "♾️ Cheksiz" if has_premium or limit == 0 else f"{limit} ta/kun"
    status = "💎 Premium" if has_premium else "🆓 Oddiy"
    
    msg = (
        f"💰 **Sizning Balansingiz**\n\n"
        f"👤 ID: `{user_id}`\n"
        f"📊 Status: **{status}**\n"
        f"📉 Limit: **{limit_text}**\n"
        f"📄 Ishlangan fayllar: **{files}** ta\n\n"
        f"Premium olish uchun: 'Premium xizmatlar 💎' tugmasini bosing."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Aloqa ✉️' button"""
    msg = (
        "📞 **Aloqa uchun:**\n\n"
        "Admin: @DastyorAI\\_Admin\n"
        "Texnik yordam: @DastyorSupport\n\n"
        "Savol yoki takliflaringizni yozib qoldirishingiz mumkin."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def help_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Yordam 🆘' button"""
    from bot.handlers.help import help_command
    await help_command(update, context)
