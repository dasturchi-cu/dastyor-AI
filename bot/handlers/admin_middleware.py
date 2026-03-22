from telegram import Update
from telegram.ext import ContextTypes
import bot.services.user_service as crm
from bot.handlers.admin import is_admin

async def track_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Middleware to track user activity with session counting"""
    if update.effective_user:
        # Check if banned first
        if crm.is_user_banned(update.effective_user.id):
            # Only block interactions, but allow admins (optional)
            if not await is_admin(update.effective_user.id):
                context.user_data['is_banned'] = True
                return

        cmd = None
        if update.message and update.message.text:
             if update.message.text.startswith('/start'): cmd = 'start'
             elif update.message.text.startswith('/'): cmd = 'command'
        
        # Shaxsiy chatda chat_id = user.id; guruhda foydalanuvchining DM id sini saqlaymiz (webdan yuborish uchun)
        private = update.effective_chat and update.effective_chat.type == "private"
        dm_chat_id = update.effective_chat.id if private else None
        crm.track_user_activity(update.effective_user, command=cmd, chat_id=dm_chat_id)
