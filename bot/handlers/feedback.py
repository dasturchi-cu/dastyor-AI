"""
Feedback Handler — Collects user feedback (text/photo/video/voice/file)
and forwards everything to a Telegram group with user info.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from bot.keyboards.reply_keyboards import get_back_button, get_main_menu
from bot.services.user_service import get_user_lang
from bot.utils.i18n import t

logger = logging.getLogger(__name__)

# ── Group where feedback is forwarded ───────────────────────────────────
FEEDBACK_GROUP_ID = -1003457224552

# ── Simple in-memory feedback counter (persistent via user_profiles.json)
def _get_feedback_count(user_id: int) -> int:
    """Get how many times user has sent feedback."""
    try:
        from bot.services.user_service import get_user_profile
        profile = get_user_profile(user_id)
        return (profile or {}).get("feedback_count", 0)
    except Exception:
        return 0


def _increment_feedback_count(user_id: int) -> int:
    """Increment and return new feedback count."""
    try:
        from bot.services.user_service import get_user_profile, _save_profiles, profiles_cache
        uid = str(user_id)
        if uid not in profiles_cache:
            return 1
        count = profiles_cache[uid].get("feedback_count", 0) + 1
        profiles_cache[uid]["feedback_count"] = count
        _save_profiles()
        return count
    except Exception as e:
        logger.error(f"Failed to increment feedback count: {e}")
        return 1


async def start_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Called when user clicks 'Aloqa ✉️'.
    Sets the state to collect feedback.
    """
    context.user_data["waiting_for"] = "feedback"
    lang = get_user_lang(update.effective_user.id) if update.effective_user else "uz_lat"

    await update.message.reply_text(
        "📩 <b>Murojaat yuborish</b>\n\n"
        "Quyidagilarni yuborishingiz mumkin:\n"
        "• 📝 Matn\n"
        "• 🖼 Rasm\n"
        "• 🎥 Video\n"
        "• 🎤 Ovozli xabar\n"
        "• 📎 Fayl\n\n"
        "<i>Yuborilgan barcha ma'lumotlar administratorga yetkaziladi.</i>",
        parse_mode="HTML",
        reply_markup=get_back_button(lang),
    )


def _build_header(user) -> str:
    """Build the feedback info header."""
    username = f"@{user.username}" if user.username else "yo'q"
    count = _get_feedback_count(user.id)
    return (
        f"📩 <b>Yangi murojaat</b>\n\n"
        f"👤 User: {username}\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"📝 Murojaat soni: <b>{count + 1}</b>"
    )


async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Process any feedback message (text/photo/video/voice/document).
    Forwards to the feedback group with user info.
    """
    message = update.message
    user = update.effective_user
    if not user:
        return

    header = _build_header(user)
    lang = get_user_lang(user.id)
    sent = False

    try:
        # ── Text feedback ───────────────────────────────────────────────
        if message.text:
            await context.bot.send_message(
                chat_id=FEEDBACK_GROUP_ID,
                text=f"{header}\n\n💬 <b>Xabar:</b>\n{message.text}",
                parse_mode="HTML",
            )
            sent = True

        # ── Photo feedback ──────────────────────────────────────────────
        elif message.photo:
            caption_text = message.caption or ""
            await context.bot.send_photo(
                chat_id=FEEDBACK_GROUP_ID,
                photo=message.photo[-1].file_id,
                caption=f"{header}\n\n🖼 Rasm bilan murojaat\n{caption_text}",
                parse_mode="HTML",
            )
            sent = True

        # ── Video feedback ──────────────────────────────────────────────
        elif message.video:
            caption_text = message.caption or ""
            await context.bot.send_video(
                chat_id=FEEDBACK_GROUP_ID,
                video=message.video.file_id,
                caption=f"{header}\n\n🎥 Video bilan murojaat\n{caption_text}",
                parse_mode="HTML",
            )
            sent = True

        # ── Voice feedback ──────────────────────────────────────────────
        elif message.voice:
            await context.bot.send_voice(
                chat_id=FEEDBACK_GROUP_ID,
                voice=message.voice.file_id,
                caption=header,
                parse_mode="HTML",
            )
            sent = True

        # ── Audio feedback ──────────────────────────────────────────────
        elif message.audio:
            await context.bot.send_audio(
                chat_id=FEEDBACK_GROUP_ID,
                audio=message.audio.file_id,
                caption=header,
                parse_mode="HTML",
            )
            sent = True

        # ── Document/File feedback ──────────────────────────────────────
        elif message.document:
            caption_text = message.caption or ""
            await context.bot.send_document(
                chat_id=FEEDBACK_GROUP_ID,
                document=message.document.file_id,
                caption=f"{header}\n\n📎 Fayl bilan murojaat\n{caption_text}",
                parse_mode="HTML",
            )
            sent = True

        # ── Video note (circular video) ─────────────────────────────────
        elif message.video_note:
            # Send header first, then video note (no caption support)
            await context.bot.send_message(
                chat_id=FEEDBACK_GROUP_ID,
                text=header,
                parse_mode="HTML",
            )
            await context.bot.send_video_note(
                chat_id=FEEDBACK_GROUP_ID,
                video_note=message.video_note.file_id,
            )
            sent = True

        if sent:
            _increment_feedback_count(user.id)
            await message.reply_text(
                "✅ Murojaatingiz qabul qilindi!\n"
                "Tez orada javob beramiz. Rahmat! 🙏",
                reply_markup=get_main_menu(user.id, lang),
            )
            # Clear state
            context.user_data.pop("waiting_for", None)
        else:
            await message.reply_text(
                "❌ Bu turdagi xabar qabul qilinmadi.\n"
                "Matn, rasm, video, ovoz yoki fayl yuboring.",
                reply_markup=get_back_button(lang),
            )

    except Exception as e:
        logger.error(f"Feedback forwarding error: {e}", exc_info=True)
        await message.reply_text(
            "❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=get_main_menu(user.id, lang),
        )
        context.user_data.pop("waiting_for", None)
