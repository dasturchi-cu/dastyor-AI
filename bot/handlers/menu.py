from telegram import Update
from telegram.ext import ContextTypes
from bot.keyboards.reply_keyboards import get_main_menu

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to main menu"""
    await update.message.reply_text(
        "📋 Asosiy menyu:",
        reply_markup=get_main_menu()
    )
