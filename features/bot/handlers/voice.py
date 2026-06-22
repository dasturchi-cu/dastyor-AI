"""Voice handlers — CV auto-fill (instant ack, background AI)."""
from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database.repositories import ai_sessions as sessions_repo
from features.ai.service import process_voice_for_cv
from features.bot.states import ObyektivkaStates
from features.cv import service as cv_service
from shared.async_db import run as db_run
from shared.keyboards import BTN_OBY, open_webapp_inline
from shared.progress import STEP_AI, STEP_AUDIO, STEP_EXTRACTED, STEP_READY, telegram_message
from shared.telegram_progress import set_step
from shared.voice import download_voice_message

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.voice | F.audio)
async def handle_voice(message: Message, bot: Bot, state: FSMContext) -> None:
    current = await state.get_state()
    if current == ObyektivkaStates.waiting_voice.state:
        return

    uid = message.from_user.id if message.from_user else 0
    status = await message.answer(telegram_message(STEP_AUDIO))
    asyncio.create_task(_handle_cv_voice_flow(message, bot, status, uid))


async def _handle_cv_voice_flow(
    message: Message, bot: Bot, status: Message, uid: int
) -> None:
    path = ""
    try:
        path = await download_voice_message(bot, message, prefix="cv_voice")
        if not path:
            await status.edit_text("❌ Audio topilmadi.")
            return

        await set_step(status, STEP_AI)
        transcript, cv_data, cv_missing = await process_voice_for_cv(path)

        await set_step(status, STEP_EXTRACTED)
        if not cv_data or len(cv_missing) > 5:
            await status.edit_text(
                f"ℹ️ CV uchun yetarli ma'lumot topilmadi.\n\n"
                f"Obyektivka uchun <b>{BTN_OBY}</b> tugmasini bosing."
            )
            return

        await db_run(cv_service.save_user_data, uid, cv_data)
        await db_run(sessions_repo.create_session, uid, "cv_voice", transcript, cv_data)

        missing_text = ""
        if cv_missing:
            missing_text = "\n\n⚠️ Yetishmayotgan: " + ", ".join(cv_missing)
        await status.edit_text(
            f"{telegram_message(STEP_READY)}\n\n"
            f"Formani tekshiring.{missing_text}",
            reply_markup=open_webapp_inline(uid, "cv"),
        )
    except Exception as e:
        logger.exception("Voice processing failed: %s", e)
        await status.edit_text(f"❌ Xatolik: {str(e)[:200]}")
    finally:
        if path:
            try:
                os.remove(path)
            except OSError:
                pass
