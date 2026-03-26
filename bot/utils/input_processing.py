import logging
import os
import time

from telegram import Update
from telegram.ext import ContextTypes

from bot.services.ai_service import transcribe_audio

logger = logging.getLogger(__name__)


async def process_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Normalize user input to plain text for form handlers.
    Supports direct text and voice/audio transcription.
    Returns empty string when input cannot be normalized.
    """
    message = update.message
    if not message:
        return ""

    text_input = (message.text or "").strip()
    if text_input:
        return text_input

    media = message.voice or message.audio
    if not media:
        return ""

    temp_path = f"temp_input_{message.from_user.id}_{int(time.time())}.ogg"
    try:
        tg_file = await media.get_file()
        await tg_file.download_to_drive(temp_path)
        transcript = (await transcribe_audio(temp_path) or "").strip()
        if transcript and not transcript.lower().startswith("audio "):
            return transcript
        return ""
    except Exception as e:
        logger.error("process_user_input voice/audio error: %s", e, exc_info=True)
        return ""
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
