"""Voice + text handlers — CV auto-fill (instant ack, background AI)."""
from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database.repositories import ai_sessions as sessions_repo
from features.ai.service import process_text_for_cv, process_voice_for_cv
from features.bot.states import CvStates, ObyektivkaStates
from features.cv import service as cv_service
from shared.ai_errors import AI_QUOTA_USER_MSG, AiQuotaError
from shared.async_db import run as db_run
from shared.keyboards import BTN_BACK, BTN_OBY, is_menu_button, open_webapp_inline
from shared.marketing import cross_sell_oby_line
from shared.progress import STEP_AI, STEP_AUDIO, STEP_EXTRACTED, STEP_READY, telegram_message
from shared.telegram_progress import set_step
from shared.voice import download_voice_message

logger = logging.getLogger(__name__)
router = Router()

CV_INSTRUCTION = (
    "📌 <b>CV uchun quyidagilarni ovoz yoki matn ko'rinishida yuboring:</b>\n\n"
    "• Ism familiya\n"
    "• Telefon, email, manzil\n"
    "• Kasb / lavozim\n"
    "• Ta'lim (OTM, yillar)\n"
    "• Ish tajribasi\n"
    "• Ko'nikmalar va tillar\n\n"
    "📝 <b>Namuna matn:</b>\n"
    "<i>Men Ali Valiyevman, Toshkent shahriman. Telefon +998901234567, "
    "email ali@gmail.com. Python dasturchiman. 2020-2024 TDYU da kompyuter fanlari "
    "bo'yicha o'qidim. 2024-yildan beri IT kompaniyada ishlayman.</i>\n\n"
    "🎙 Ovozli xabar yoki 📝 matn yuboring."
)


@router.message(F.voice | F.audio)
async def handle_voice(message: Message, bot: Bot, state: FSMContext) -> None:
    current = await state.get_state()
    if current == ObyektivkaStates.waiting_voice.state:
        return

    uid = message.from_user.id if message.from_user else 0
    status = await message.answer(telegram_message(STEP_AUDIO))
    asyncio.create_task(_handle_cv_voice_flow(message, bot, status, uid, state))


@router.message(CvStates.waiting_input, F.text)
async def cv_text_fill(message: Message, state: FSMContext) -> None:
    if not message.text or message.text.startswith("/"):
        return
    if message.text == BTN_BACK or message.text.casefold() == "bekor":
        return
    if is_menu_button(message.text):
        from features.bot.handlers.start import menu_from_flow_waiting

        await menu_from_flow_waiting(message, state)
        return
    uid = message.from_user.id if message.from_user else 0
    status = await message.answer("✅ Matn qabul qilindi\n⏳ AI tahlil qilmoqda...")
    asyncio.create_task(_handle_cv_text_flow(message.text or "", status, uid, state))


async def _handle_cv_text_flow(text: str, status: Message, uid: int, state: FSMContext) -> None:
    try:
        transcript, cv_data, cv_missing = await process_text_for_cv(text)
        if not cv_data or len(cv_missing) > 6:
            await status.edit_text(
                "ℹ️ CV uchun yetarli ma'lumot topilmadi.\n"
                "Namunadagi kabi to'liqroq yozing."
            )
            return
        await db_run(cv_service.save_user_data, uid, cv_data)
        await db_run(sessions_repo.create_session, uid, "cv_voice", transcript, cv_data)
        await state.clear()
        missing_text = ""
        if cv_missing:
            missing_text = "\n\n⚠️ Yetishmayotgan: " + ", ".join(cv_missing)
        await status.edit_text(
            f"{telegram_message(STEP_READY)}\n\n"
            f"CV formasi to'ldirildi.{missing_text}"
            f"{cross_sell_oby_line()}",
            reply_markup=open_webapp_inline(uid, "cv"),
        )
    except AiQuotaError:
        await status.edit_text(AI_QUOTA_USER_MSG)
    except Exception as e:
        logger.exception("CV text fill failed: %s", e)
        await status.edit_text(f"❌ Xatolik: {str(e)[:200]}")


async def _handle_cv_voice_flow(
    message: Message, bot: Bot, status: Message, uid: int, state: FSMContext
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
        if not cv_data or len(cv_missing) > 6:
            await status.edit_text(
                f"ℹ️ CV uchun yetarli ma'lumot topilmadi.\n\n"
                f"Namunadagi tartibda qayta yuboring yoki <b>{BTN_OBY}</b> tanlang."
            )
            return

        await db_run(cv_service.save_user_data, uid, cv_data)
        await db_run(sessions_repo.create_session, uid, "cv_voice", transcript, cv_data)
        await state.clear()

        missing_text = ""
        if cv_missing:
            missing_text = "\n\n⚠️ Yetishmayotgan: " + ", ".join(cv_missing)
        await status.edit_text(
            f"{telegram_message(STEP_READY)}\n\n"
            f"Formani tekshiring.{missing_text}"
            f"{cross_sell_oby_line()}",
            reply_markup=open_webapp_inline(uid, "cv"),
        )
    except AiQuotaError:
        await status.edit_text(AI_QUOTA_USER_MSG)
    except Exception as e:
        logger.exception("Voice processing failed: %s", e)
        await status.edit_text(f"❌ Xatolik: {str(e)[:200]}")
    finally:
        if path:
            try:
                os.remove(path)
            except OSError:
                pass
