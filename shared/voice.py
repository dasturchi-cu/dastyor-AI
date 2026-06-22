"""Shared Telegram voice download."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from aiogram import Bot
from aiogram.types import Message


from config.paths import temp_dir


async def download_voice_message(bot: Bot, message: Message, *, prefix: str = "voice") -> str | None:
    if message.voice:
        file = await bot.get_file(message.voice.file_id)
        ext = ".ogg"
    elif message.audio:
        file = await bot.get_file(message.audio.file_id)
        ext = Path(message.audio.file_name or "").suffix or ".mp3"
        if len(ext) > 8:
            ext = ".mp3"
    else:
        return None

    os.makedirs(str(temp_dir()), exist_ok=True)
    fd, path = tempfile.mkstemp(suffix=ext, prefix=f"{prefix}_", dir=str(temp_dir()))
    os.close(fd)
    await bot.download_file(file.file_path, path)
    return path
