from telegram import Update
from telegram.ext import ContextTypes
from bot.services.user_service import get_user_profile, get_user_lang
from bot.services.settings_service import (
    get_active_plan_code,
    get_active_subscription_expires_display,
    get_premium_status,
    get_premium_expiry,
)
from bot.services.usage_tracker import (
    format_tariff_status_markdown,
    get_effective_daily_cap,
    get_remaining,
    get_user_usage,
    has_paid_active_plan,
)
from bot.utils.i18n import t

async def balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Balans 💰' button"""
    if not update.effective_chat or update.effective_chat.type != "private":
        return

    user_id = update.effective_user.id
    profile = get_user_profile(user_id)

    files = profile.get("files_processed", 0) if profile else 0

    lang = get_user_lang(user_id)
    plan = get_active_plan_code(user_id)
    if plan == "premium":
        status = t("status_prem", lang)
    elif plan == "standard":
        status = t("status_standard", lang)
    else:
        status = t("status_free", lang)

    if has_paid_active_plan(user_id):
        limit_text = t("limit_unlim", lang)
    else:
        cap = get_effective_daily_cap()
        if cap <= 0:
            limit_text = t("limit_unlim", lang)
        else:
            used = get_user_usage(user_id)
            rem = get_remaining(user_id)
            limit_text = (
                f"{t('limit_daily', lang, limit=cap)} "
                f"— bugun: {used}/{cap}, qoldi: {rem}"
            )

    premium_btn = t("btn_premium", lang)

    head = format_tariff_status_markdown(user_id)
    msg = head + "\n\n" + t("balance_msg", lang, user_id=user_id, status=status, limit_text=limit_text, files=files, premium_btn=premium_btn)
    exp_disp = get_active_subscription_expires_display(user_id)
    if plan in ("standard", "premium") and exp_disp:
        msg += f"\n\n📅 Obuna tugashi: `{exp_disp}`"
    p_status = get_premium_status(user_id)
    if p_status == "expired":
        exp = get_premium_expiry(user_id) or "-"
        msg += f"\n\n⚠️ Premium muddati tugagan ({exp}). Yangilash mumkin."
    await update.message.reply_text(msg, parse_mode="Markdown")

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Aloqa ✉️' button"""
    if not update.effective_chat or update.effective_chat.type != "private":
        return
    lang = get_user_lang(update.effective_user.id)
    msg = t("contact_msg", lang)
    await update.message.reply_text(msg, parse_mode="Markdown")

async def help_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Yordam 🆘' button"""
    if not update.effective_chat or update.effective_chat.type != "private":
        return
    from bot.handlers.help import help_command
    await help_command(update, context)
