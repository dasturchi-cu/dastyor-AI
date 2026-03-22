import asyncio

from telegram import Update
from telegram.ext import ContextTypes
from bot.services.user_service import get_user_profile, get_user_lang
from bot.services.settings_service import get_premium_status, get_premium_expiry
from bot.services.usage_tracker import format_tariff_status_markdown, get_tariff_snapshot
from bot.utils.i18n import t


def _balance_bundle(user_id: int):
    """Sinxron: Supabase/JSON — async handler uchun to_thread ichida."""
    profile = get_user_profile(user_id)
    lang = get_user_lang(user_id)
    snap = get_tariff_snapshot(user_id)
    return profile, lang, snap


async def balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Balans 💰' button"""
    if not update.effective_chat or update.effective_chat.type != "private":
        return

    user_id = update.effective_user.id
    try:
        profile, lang, snap = await asyncio.to_thread(_balance_bundle, user_id)
    except Exception:
        profile = get_user_profile(user_id)
        lang = get_user_lang(user_id)
        snap = get_tariff_snapshot(user_id)

    files = profile.get("files_processed", 0) if profile else 0
    plan = snap["plan"]
    if plan == "premium":
        status = t("status_prem", lang)
    elif plan == "standard":
        status = t("status_standard", lang)
    else:
        status = t("status_free", lang)

    breakdown = snap["limits_breakdown"]
    limit_text = "\n".join(f"• {row['display']}" for row in breakdown)

    premium_btn = t("btn_premium", lang)

    head = format_tariff_status_markdown(user_id, snapshot=snap)
    msg = head + "\n\n" + t("balance_msg", lang, user_id=user_id, status=status, limit_text=limit_text, files=files, premium_btn=premium_btn)
    exp_disp = snap.get("subscription_ends")
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
    try:
        lang = await asyncio.to_thread(get_user_lang, update.effective_user.id)
    except Exception:
        lang = get_user_lang(update.effective_user.id)
    msg = t("contact_msg", lang)
    await update.message.reply_text(msg, parse_mode="Markdown")

async def help_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Yordam 🆘' button"""
    if not update.effective_chat or update.effective_chat.type != "private":
        return
    from bot.handlers.help import help_command
    await help_command(update, context)
