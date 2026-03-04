"""
/start command with deep-link action support.

New deep-link format:  /start <action>
  action: cv | obyektivka | ocr | pdf | translit | translate | premium

On /start with a known action the bot:
  1. Greets the user
  2. Sends an inline button that opens the EXACT webapp page
  3. Passes telegram_id in the URL so the site can call /api/auth

On plain /start (no payload) it shows the full service menu.
"""
import os
from telegram import Update, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from bot.keyboards.reply_keyboards import get_main_menu
from bot.services.user_service import get_user_lang, set_user_lang, save_chat_id
from bot.utils.i18n import t

WEBAPP_BASE  = os.getenv("WEBAPP_BASE",  "https://dastyor-ai.onrender.com/webapp")
BOT_USERNAME = os.getenv("BOT_USERNAME", "DastyorAiBot")

# Map deep-link payload → (page_file, button_label, description)
_ACTION_MAP: dict[str, tuple[str, str, str]] = {
    "cv"         : ("cv.html",          "📄 CV Yaratish",          "Professional CV tayyorlash"),
    "obyektivka" : ("obyektivka.html",   "📋 Obyektivka",           "Ma'lumotnoma tayyorlash"),
    "ocr"        : ("ocr.html",          "📸 Rasm → Word",          "Rasmdan matn ajratish"),
    "pdf"        : ("img2pdf.html",      "🖼 Rasm → PDF",           "Rasmlarni PDFga birlashtirish"),
    "translit"   : ("translit.html",     "🔤 Krill ↔ Lotin",        "Matnni aylantirish"),
    "translate"  : ("translate.html",    "🌐 Tarjima",              "Matn tarjima qilish"),
    "premium"    : ("premium.html",      "💎 Premium",              "Premium tarif haqida ma'lumot"),
}


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start [action] — with optional deep-link payload."""
    user = update.effective_user
    if not user:
        return

    uid = user.id
    first_name = user.first_name or "Do'stim"

    lang = get_user_lang(uid)

    # ── Persist chat_id immediately so file delivery always works ──────
    save_chat_id(uid, update.effective_chat.id if update.effective_chat else uid)

    # ── Check payload ──────────────────────────────────────────────────
    payload = (context.args[0] if context.args else "").strip().lower()
    action  = _ACTION_MAP.get(payload)

    if action:
        # ── Deep-link: open specific tool directly ───────────────────
        page_file, btn_label, description = action
        url = f"{WEBAPP_BASE}/{page_file}?telegram_id={uid}&lang={lang}"

        text = (
            f"Assalomu alaykum, {first_name}! 👋\n\n"
            f"🚀 <b>{description}</b>:"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(btn_label, web_app=WebAppInfo(url=url))
        ]])
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
        return

    # ── Default /start — Ask for language ────────────────────────────
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇿 O'zbek (Lotin)", callback_data="lang_uz_lat"), InlineKeyboardButton("🇺🇿 Ўзбек (Кир)", callback_data="lang_uz_cyr")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"), InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
    ])
    await update.message.reply_text(t("choose_lang", lang), reply_markup=kb)


async def language_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    first_name = query.from_user.first_name or "Do'stim"
    await query.answer()

    lang_code = query.data.replace("lang_", "")
    set_user_lang(uid, lang_code)

    await query.edit_message_text(t("lang_saved", lang_code))

    welcome_text = t("welcome", lang_code, name=first_name)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            t("btn_app", lang_code),
            web_app=WebAppInfo(url=f"{WEBAPP_BASE}/index.html?telegram_id={uid}&lang={lang_code}")
        )],
        [
            InlineKeyboardButton(
                t("btn_oby", lang_code),
                web_app=WebAppInfo(url=f"{WEBAPP_BASE}/obyektivka.html?telegram_id={uid}&lang={lang_code}")
            ),
            InlineKeyboardButton(
                t("btn_cv", lang_code),
                web_app=WebAppInfo(url=f"{WEBAPP_BASE}/cv.html?telegram_id={uid}&lang={lang_code}")
            ),
        ],
        [
            InlineKeyboardButton(
                t("btn_ocr", lang_code),
                web_app=WebAppInfo(url=f"{WEBAPP_BASE}/ocr.html?telegram_id={uid}&lang={lang_code}")
            ),
            InlineKeyboardButton(
                t("btn_premium", lang_code),
                web_app=WebAppInfo(url=f"{WEBAPP_BASE}/premium.html?telegram_id={uid}&lang={lang_code}")
            ),
        ],
    ])

    await context.bot.send_message(
        chat_id=uid,
        text=welcome_text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await context.bot.send_message(
        chat_id=uid,
        text=t("or_menu", lang_code),
        reply_markup=get_main_menu(uid, lang_code),
    )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /menu"""
    uid = update.effective_user.id if update.effective_user else None
    lang = get_user_lang(uid)
    await update.message.reply_text(
        t("or_menu", lang).replace("👇 ", ""),
        reply_markup=get_main_menu(uid, lang),
        parse_mode="HTML",
    )
