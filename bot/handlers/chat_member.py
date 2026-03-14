from telegram import Update, ChatMember
from telegram.ext import ContextTypes
import bot.services.user_service as crm
import logging

logger = logging.getLogger(__name__)

async def chat_member_updated(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle chat member updates (block/unblock bot)"""
    result = update.chat_member

    if not result:
        return

    new_member = result.new_chat_member
    
    # If bot was blocked (user stopped/blocked bot)
    if new_member.status == ChatMember.KICKED:
        crm.set_user_blocked_bot(new_member.user.id, True)
        logger.info(f"User {new_member.user.id} blocked the bot.")

    # If bot was unblocked (user restarted bot)
    # Note: Usually restart also triggers /start, which updates 'blocked_bot' to False anyway.
    elif new_member.status == ChatMember.MEMBER:
        crm.set_user_blocked_bot(new_member.user.id, False)
        logger.info(f"User {new_member.user.id} unblocked the bot.")
