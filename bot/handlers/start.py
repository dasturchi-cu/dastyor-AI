from telegram import Update
from telegram.ext import ContextTypes
from bot.keyboards.reply_keyboards import get_main_menu

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /start command.
    Shows branded welcome message and main grid menu.
    """
    if update.effective_user:
        user_first_name = update.effective_user.first_name
        
        welcome_text = (
            f"Assalomu alaykum, {user_first_name}! 👋\n\n"
            "🤖 **LASHBOT — AI Hujjat Servis**\n\n"
            "Men sizga quyidagi xizmatlarda yordam beraman:\n\n"
            "✨ Obyektivka avtomatik tayyorlash\n"
            "📄 Rasm → Word konvertatsiya\n"
            "🔤 Kirill-Lotin transliteratsiya\n"
            "🌐 Hujjat tarjimasi\n"
            "📑 Rasm → PDF birlashtiruv\n"
            "✅ Imlo tekshirish\n\n"
            "Quyidagi menyudan kerakli xizmatni tanlang:"
        )
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_main_menu(),
            parse_mode="Markdown"
        )

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /menu"""
    await update.message.reply_text("🏠 **Bosh menyu**", reply_markup=get_main_menu(), parse_mode="Markdown")
