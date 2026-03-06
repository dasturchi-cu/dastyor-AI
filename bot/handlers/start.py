"""
/start command handler — prямо menuni ko'rsatadi (til so'ramasdan).

Deep-link format:  /start <action>
  action: cv | obyektivka | ocr | pdf | translit | translate | premium

Oddiy /start: to'g'ridan-to'g'ri menuni ko'rsatadi.
"""
import os
from telegram import Update, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from bot.keyboards.reply_keyboards import get_main_menu
from bot.services.user_service import get_user_lang, save_chat_id
from bot.utils.i18n import t

WEBAPP_BASE  = os.getenv("WEBAPP_BASE",  "https://dastyor-ai.onrender.com/webapp")
BOT_USERNAME = os.getenv("BOT_USERNAME", "DastyorAiBot")

# Default til — o'zbek lotin
DEFAULT_LANG = "uz_lat"

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

    # Har doim o'zbek tili (bot uchun til tanlash yo'q)
    lang = DEFAULT_LANG

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

    # ── Default /start — to'g'ridan-to'g'ri menuni ko'rsat ──────────
    welcome_text = (
        f"Assalomu alaykum, <b>{first_name}</b>! 👋\n\n"
        f"🤖 <b>DASTYOR AI</b> — hujjat tayyorlash assistantingiz!\n\n"
        f"📋 <b>Nima qila olaman:</b>\n"
        f"• Obyektivka tayyorlash\n"
        f"• CV (rezyume) yaratish\n"
        f"• Rasmdan matn ajratish (OCR)\n"
        f"• Krill ↔ Lotin aylantirish\n"
        f"• Matn tarjima qilish\n"
        f"• Rasmlarni PDFga birlashtirish\n\n"
        f"👇 Quyidagi menyudan xizmat tanlang:"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📋 Obyektivka",
                web_app=WebAppInfo(url=f"{WEBAPP_BASE}/obyektivka.html?telegram_id={uid}&lang={lang}")
            ),
            InlineKeyboardButton(
                "📄 CV yaratish",
                web_app=WebAppInfo(url=f"{WEBAPP_BASE}/cv.html?telegram_id={uid}&lang={lang}")
            ),
        ],
        [
            InlineKeyboardButton(
                "🔤 Krill ↔ Lotin",
                web_app=WebAppInfo(url=f"{WEBAPP_BASE}/translit.html?telegram_id={uid}&lang={lang}")
            ),
            InlineKeyboardButton(
                "🌐 Tarjima",
                web_app=WebAppInfo(url=f"{WEBAPP_BASE}/translate.html?telegram_id={uid}&lang={lang}")
            ),
        ],
        [
            InlineKeyboardButton(
                "📸 Rasm → Word",
                web_app=WebAppInfo(url=f"{WEBAPP_BASE}/ocr.html?telegram_id={uid}&lang={lang}")
            ),
            InlineKeyboardButton(
                "🖼 Rasm → PDF",
                web_app=WebAppInfo(url=f"{WEBAPP_BASE}/img2pdf.html?telegram_id={uid}&lang={lang}")
            ),
        ],
        [
            InlineKeyboardButton(
                "💎 Premium",
                web_app=WebAppInfo(url=f"{WEBAPP_BASE}/premium.html?telegram_id={uid}&lang={lang}")
            ),
        ],
    ])

    await update.message.reply_text(
        welcome_text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await update.message.reply_text(
        "🚀 Appni ochish uchun pastdagi tugmani bosing:",
        reply_markup=get_main_menu(uid, lang),
    )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /menu"""
    uid = update.effective_user.id if update.effective_user else None
    await update.message.reply_text(
        "Menyudan xizmat tanlang:",
        reply_markup=get_main_menu(uid, DEFAULT_LANG),
        parse_mode="HTML",
    )
