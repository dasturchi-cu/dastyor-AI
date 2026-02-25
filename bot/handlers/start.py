from telegram import Update
from telegram.ext import ContextTypes
from bot.keyboards.reply_keyboards import get_main_menu

from telegram import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /start command.
    Shows branded welcome message and Web App launch buttons.
    """
    if update.effective_user:
        user_first_name = update.effective_user.first_name
        
        welcome_text = (
            f"Assalomu alaykum, {user_first_name}! 👋\n\n"
            "🚀 **DASTYOR AI — Hujjat Servisiga xush kelibsiz!**\n\n"
            "Endi barcha xizmatlarimizdan qulay **Web App (Mini App)** interfeysi orqali foydalanishingiz mumkin.\n\n"
            "✨ Obyektivka tayyorlash\n"
            "📄 CV yaratish (Professional)\n"
            "🌐 Tarjima va OCR xizmatlari\n\n"
            "Pastdagi 🚀 **Appni ochish** tugmasini bosing:"
        )
        
        # Web App URL from Render
        web_app_url = "https://dastyor-ai.onrender.com/webapp/index.html"
        
        inline_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Appni ochish", web_app=WebAppInfo(url=web_app_url))],
            [InlineKeyboardButton("💎 Premium", web_app=WebAppInfo(url=f"{web_app_url.replace('index.html', 'premium.html')}"))]
        ])
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=inline_keyboard,
            parse_mode="Markdown"
        )

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /menu"""
    await update.message.reply_text("🏠 **Bosh menyu**", reply_markup=get_main_menu(), parse_mode="Markdown")
