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

    # ── Check payload ──────────────────────────────────────────────────
    payload = (context.args[0] if context.args else "").strip().lower()
    action  = _ACTION_MAP.get(payload)

    if action:
        # ── Deep-link: open specific tool directly ───────────────────
        page_file, btn_label, description = action
        url = f"{WEBAPP_BASE}/{page_file}?telegram_id={uid}"

        text = (
            f"Assalomu alaykum, {first_name}! 👋\n\n"
            f"🚀 <b>{description}</b> uchun quyidagi tugmani bosing:"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(btn_label, web_app=WebAppInfo(url=url))
        ]])
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
        return

    # ── Default /start — full welcome menu ────────────────────────────
    welcome_text = (
        f"Assalomu alaykum, {first_name}! 👋\n\n"
        "🚀 <b>DASTYOR AI</b> — hujjat va AI xizmatlar platformasi.\n\n"
        "✨ Barcha xizmatlar:\n"
        "• 📋 Obyektivka / Ma'lumotnoma\n"
        "• 📄 CV / Rezyume yaratish\n"
        "• 📸 Rasimdan Word / PDF\n"
        "• 🌐 Tarjima (UZ ↔ EN ↔ RU)\n"
        "• 🔤 Krill ↔ Lotin konvertatsiya\n"
        "• ✏️ Imlo tekshirish\n\n"
        "Quyidagi tugmani bosib <b>Mini App</b>ni oching:"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🚀 Appni ochish",
            web_app=WebAppInfo(url=f"{WEBAPP_BASE}/index.html?telegram_id={uid}")
        )],
        [
            InlineKeyboardButton(
                "📋 Obyektivka",
                web_app=WebAppInfo(url=f"{WEBAPP_BASE}/obyektivka.html?telegram_id={uid}")
            ),
            InlineKeyboardButton(
                "📄 CV",
                web_app=WebAppInfo(url=f"{WEBAPP_BASE}/cv.html?telegram_id={uid}")
            ),
        ],
        [
            InlineKeyboardButton(
                "📸 OCR",
                web_app=WebAppInfo(url=f"{WEBAPP_BASE}/ocr.html?telegram_id={uid}")
            ),
            InlineKeyboardButton(
                "💎 Premium",
                web_app=WebAppInfo(url=f"{WEBAPP_BASE}/premium.html?telegram_id={uid}")
            ),
        ],
    ])

    await update.message.reply_text(
        welcome_text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    # Also show the reply keyboard for quick access inside the chat
    await update.message.reply_text(
        "📌 Yoki menyudan tanlang:",
        reply_markup=get_main_menu(uid),
    )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /menu"""
    uid = update.effective_user.id if update.effective_user else None
    await update.message.reply_text(
        "🏠 <b>Bosh menyu</b>",
        reply_markup=get_main_menu(uid),
        parse_mode="HTML",
    )
