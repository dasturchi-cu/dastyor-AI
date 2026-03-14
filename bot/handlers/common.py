from telegram import Update
from telegram.ext import ContextTypes
from bot.services.user_service import get_user_profile, get_user_lang
from bot.services.settings_service import get_daily_limit
from bot.utils.i18n import t

async def balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Balans 💰' button"""
    user_id = update.effective_user.id
    profile = get_user_profile(user_id)
    limit = get_daily_limit()
    
    files = profile.get("files_processed", 0) if profile else 0
    
    # Check premium
    from bot.services.settings_service import is_premium
    has_premium = is_premium(user_id)
    lang = get_user_lang(user_id)
    
    limit_text = t("limit_unlim", lang) if has_premium or limit == 0 else t("limit_daily", lang, limit=limit)
    status = t("status_prem", lang) if has_premium else t("status_free", lang)
    premium_btn = t("btn_premium", lang)
    
    msg = t("balance_msg", lang, user_id=user_id, status=status, limit_text=limit_text, files=files, premium_btn=premium_btn)
    await update.message.reply_text(msg, parse_mode="Markdown")

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Aloqa ✉️' button"""
    lang = get_user_lang(update.effective_user.id)
    msg = t("contact_msg", lang)
    await update.message.reply_text(msg, parse_mode="Markdown")

async def help_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Yordam 🆘' button"""
    from bot.handlers.help import help_command
    await help_command(update, context)
