"""
/start command handler — prямо menuni ko'rsatadi (til so'ramasdan).

Deep-link format:  /start <action>
  action: cv | obyektivka | ocr | pdf | translit | translate | premium

Oddiy /start: to'g'ridan-to'g'ri menuni ko'rsatadi.
"""
import asyncio
import logging
import os
from io import BytesIO

from telegram import InputFile, Update, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from bot.keyboards.reply_keyboards import get_main_menu
from bot.services.user_service import save_chat_id
from bot.services.usage_tracker import format_tariff_status_html
from config import WEBAPP_BASE

logger = logging.getLogger(__name__)

BOT_USERNAME = os.getenv("BOT_USERNAME", "DastyorAiBot")
# To‘g‘ridan-to‘g‘ri rasm URL (ibb.co sahifa emas — i.ibb.co … .jpg/.png).
# Env bo‘lmasa — ImgBB’dagi default intro (faqat botda ishlatiladi, WebAppda emas).
_DEFAULT_START_INTRO_URL = (
    "https://i.ibb.co/XxFxhc1F/image-a640d915-8968-4912-aade-96b57ca803dc.jpg"
)
_raw_intro_url = os.getenv("START_INTRO_PHOTO_URL")
START_INTRO_PHOTO_URL = (
    _DEFAULT_START_INTRO_URL if _raw_intro_url is None else str(_raw_intro_url).strip()
)
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


def _hero_intro_photo_path() -> str | None:
    """Loyihadagi webapp hero rasmi (deployda repo ildizida bo‘lishi kerak)."""
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    p = os.path.join(root, "webapp", "assets", "hero-dastyor.png")
    return p if os.path.isfile(p) else None


async def _send_start_intro_photo(message, first_name: str) -> bool:
    """Avval HTTPS URL, keyin mahalliy fayl (Telegram to‘g‘ri rasm havolasini talab qiladi)."""
    caption = (
        f"Assalomu alaykum, <b>{first_name}</b>! 👋\n\n"
        f"✨ <b>Siz yozasiz — DASTYOR AI bajaradi!</b>"
    )
    path = _hero_intro_photo_path()
    url = START_INTRO_PHOTO_URL
    try:
        if url.startswith("https://") or url.startswith("http://"):
            try:
                await message.reply_photo(photo=url, caption=caption, parse_mode="HTML")
                return True
            except Exception as e:
                logger.warning("Start intro URL rasm yuborilmadi, mahalliy fayl sinanadi: %s", e)
        if path:
            with open(path, "rb") as f:
                data = f.read()
            bio = BytesIO(data)
            await message.reply_photo(
                photo=InputFile(bio, filename="dastyor-hero.png"),
                caption=caption,
                parse_mode="HTML",
            )
            return True
    except Exception as e:
        logger.warning("Start intro rasm yuborilmadi: %s", e)
    if not path and not (url.startswith("https://") or url.startswith("http://")):
        logger.warning(
            "Start intro: na URL, na webapp/assets/hero-dastyor.png. "
            "START_INTRO_PHOTO_URL yoki fayl qo‘shing."
        )
    return False


async def _merge_tariff_into_message(message, uid: int, reply_markup, *, prefix: str = "", suffix: str = ""):
    """Tarif blokini thread-da yuklab, xabarni tahrirlaydi — /start javobini bloklamaydi."""
    try:
        tb = await asyncio.to_thread(format_tariff_status_html, uid)
        parts = [p for p in (prefix.strip(), tb, suffix.strip()) if p]
        text = "\n\n".join(parts)
        await message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        logger.debug("tariff merge edit skipped (user_id=%s)", uid, exc_info=True)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start [action] — with optional deep-link payload."""
    if not update.effective_chat or update.effective_chat.type != "private":
        return
    user = update.effective_user
    if not user:
        return

    uid = user.id
    first_name = user.first_name or "Do'stim"

    # Har doim o'zbek tili (bot uchun til tanlash yo'q)
    lang = DEFAULT_LANG

    # chat_id DBga yozish — javobni sekinlatmasin (fon-da)
    chat_id_persistent = update.effective_chat.id if update.effective_chat else uid
    try:
        asyncio.create_task(asyncio.to_thread(save_chat_id, uid, chat_id_persistent))
    except Exception:
        save_chat_id(uid, chat_id_persistent)

    # ── Check payload ──────────────────────────────────────────────────
    payload = (context.args[0] if context.args else "").strip().lower()

    # ── Referral deep-link: /start ref_<inviter_id> ─────────────────────
    # Example: https://t.me/DastyorAiBot?start=ref_123456
    try:
        if payload.startswith("ref_") or payload.startswith("ref"):
            raw = payload.replace("ref_", "").replace("ref", "").strip()
            if raw.isdigit():
                inviter = int(raw)
                if inviter and inviter != int(uid):
                    from bot.services.supabase_db import has_db, db_register_referral
                    if has_db():
                        db_register_referral(inviter, int(uid))
    except Exception:
        logger.debug("referral start payload failed", exc_info=True)

    action  = _ACTION_MAP.get(payload)

    if action:
        # ── Deep-link: rasm yubormaymiz (foydalanuvchi so'ragan) ─────
        page_file, btn_label, description = action
        url = f"{WEBAPP_BASE}/{page_file}?telegram_id={uid}&lang={lang}"

        text_base = (
            f"Assalomu alaykum, <b>{first_name}</b>! 👋\n\n"
            f"🚀 <b>{description}</b>:"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(btn_label, web_app=WebAppInfo(url=url))
        ]])
        msg = await update.message.reply_text(text_base, reply_markup=keyboard, parse_mode="HTML")
        asyncio.create_task(_merge_tariff_into_message(msg, uid, keyboard, prefix=text_base))
        return

    # ── Default /start — rasm yubormaymiz, 1 ta xabar + reply menu ──
    welcome_text = (
        f"Assalomu alaykum, <b>{first_name}</b>! 👋\n\n"
        f"✨ <b>Siz yozasiz — DASTYOR AI bajaradi!</b>\n"
        f"DASTYOR yordamida har qanday hujjat bilan professional darajada ishlang.\n\n"
        f"🤖 <b>DASTYOR AI</b> — hujjat tayyorlash assistantingiz!\n\n"
        + f"📋 <b>Nima qila olaman:</b>\n"
        f"• Obyektivka tayyorlash\n"
        f"• CV (rezyume) yaratish\n"
        f"• Rasmdan matn ajratish (OCR)\n"
        f"• Krill ↔ Lotin aylantirish\n"
        f"• Matn tarjima qilish\n"
        f"• Rasmlarni PDFga birlashtirish\n\n"
        f"👇 Quyidagi menyudan xizmat tanlang:"
    )

    kb = get_main_menu(uid, lang)
    msg = await update.message.reply_text(welcome_text, reply_markup=kb, parse_mode="HTML")
    asyncio.create_task(_merge_tariff_into_message(msg, uid, kb, prefix=welcome_text))


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /menu"""
    if not update.effective_chat or update.effective_chat.type != "private":
        return
    uid = update.effective_user.id if update.effective_user else None
    if not uid:
        return
    kb = get_main_menu(uid, DEFAULT_LANG)
    msg = await update.message.reply_text(
        "Menyudan xizmat tanlang:",
        reply_markup=kb,
        parse_mode="HTML",
    )
    asyncio.create_task(_merge_tariff_into_message(msg, uid, kb, suffix="Menyudan xizmat tanlang:"))
