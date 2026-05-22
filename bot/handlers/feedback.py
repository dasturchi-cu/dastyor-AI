"""
Feedback Handler — Collects user feedback (text/photo/video/voice/file)
and forwards everything to a Telegram group with user info.
"""
import logging
import os
from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes
from bot.flow.state import WAITING_FOR_FEEDBACK
from bot.ui.keyboards import contact_button_labels, help_button_labels, user_reply_menu
from bot.ui.messages import (
    SUPPORT_CANCEL_TEXT,
    SUPPORT_INVALID_TEXT,
    SUPPORT_START_TEXT,
    SUPPORT_SUCCESS_TEXT,
)

logger = logging.getLogger(__name__)

# ── Group where feedback is forwarded ───────────────────────────────────
FEEDBACK_GROUP_ID = int((os.getenv("SUPPORT_GROUP_ID") or "-1003457224552").strip())

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
        from bot.services.user_service import _save_profiles, profiles_cache
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
    msg = update.message
    if not msg and update.callback_query:
        msg = update.callback_query.message
    if not msg:
        return
    context.user_data["waiting_for"] = WAITING_FOR_FEEDBACK
    uid = int(update.effective_user.id) if update.effective_user else 0
    if uid:
        try:
            from bot.services.bot_analytics import log_bot_event

            log_bot_event(uid, "bot_support_start")
        except Exception:
            pass

    await msg.reply_text(
        SUPPORT_START_TEXT,
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
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
    if not message or not user:
        return

    header = _build_header(user)
    sent = False

    try:
        request_text_for_panel = ""
        # ── Text feedback ───────────────────────────────────────────────
        if message.text:
            text_stripped = message.text.strip()
            if text_stripped.startswith("/"):
                return
            if text_stripped in contact_button_labels() or text_stripped in help_button_labels():
                await start_feedback(update, context)
                return
            if text_stripped.lower() in {"bekor", "cancel", "orqaga", "ortga"}:
                context.user_data.pop("waiting_for", None)
                base = context.bot_data.get("webapp_base", "")
                await message.reply_text(
                    SUPPORT_CANCEL_TEXT,
                    reply_markup=user_reply_menu(base, user.id),
                    parse_mode="HTML",
                )
                return
            request_text_for_panel = message.text
            await context.bot.send_message(
                chat_id=FEEDBACK_GROUP_ID,
                text=f"{header}\n\n💬 <b>Xabar:</b>\n{message.text}",
                parse_mode="HTML",
            )
            sent = True

        # ── Photo feedback ──────────────────────────────────────────────
        elif message.photo:
            caption_text = message.caption or ""
            request_text_for_panel = caption_text or "[Photo attachment]"
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
            request_text_for_panel = caption_text or "[Video attachment]"
            await context.bot.send_video(
                chat_id=FEEDBACK_GROUP_ID,
                video=message.video.file_id,
                caption=f"{header}\n\n🎥 Video bilan murojaat\n{caption_text}",
                parse_mode="HTML",
            )
            sent = True

        # ── Voice feedback ──────────────────────────────────────────────
        elif message.voice:
            request_text_for_panel = "Ovozli xabar"
            await context.bot.send_voice(
                chat_id=FEEDBACK_GROUP_ID,
                voice=message.voice.file_id,
                caption=f"{header}\n\n🎙 Ovozli xabar",
                parse_mode="HTML",
            )
            sent = True

        # ── Audio feedback ──────────────────────────────────────────────
        elif message.audio:
            request_text_for_panel = "Audio fayl"
            await context.bot.send_audio(
                chat_id=FEEDBACK_GROUP_ID,
                audio=message.audio.file_id,
                caption=f"{header}\n\n🎵 Audio",
                parse_mode="HTML",
            )
            sent = True

        # ── Document/File feedback ──────────────────────────────────────
        elif message.document:
            caption_text = message.caption or ""
            request_text_for_panel = caption_text or f"[Document: {message.document.file_name or 'file'}]"
            await context.bot.send_document(
                chat_id=FEEDBACK_GROUP_ID,
                document=message.document.file_id,
                caption=f"{header}\n\n📎 Fayl bilan murojaat\n{caption_text}",
                parse_mode="HTML",
            )
            sent = True

        # ── Video note (circular video) ─────────────────────────────────
        elif message.video_note:
            request_text_for_panel = "[Video note]"
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
            try:
                from bot.services.support_service import create_support_request
                create_support_request(
                    user_id=user.id,
                    username=user.username or "",
                    message=request_text_for_panel or "[Support media message]",
                    source="bot",
                )
            except Exception as panel_err:
                logger.warning(f"Support panel save failed: {panel_err}")

            _increment_feedback_count(user.id)
            base = context.bot_data.get("webapp_base", "")
            await message.reply_text(
                SUPPORT_SUCCESS_TEXT,
                reply_markup=user_reply_menu(base, user.id),
                parse_mode="HTML",
            )
            # Clear state
            context.user_data.pop("waiting_for", None)
        else:
            await message.reply_text(
                SUPPORT_INVALID_TEXT,
                parse_mode="HTML",
            )

    except Exception as e:
        logger.error(f"Feedback forwarding error: {e}", exc_info=True)
        base = context.bot_data.get("webapp_base", "")
        await message.reply_text(
            "❌ Yuborib bo‘lmadi. Qayta urinib ko‘ring yoki /contact.",
            reply_markup=user_reply_menu(base, user.id),
            parse_mode="HTML",
        )
        context.user_data.pop("waiting_for", None)
