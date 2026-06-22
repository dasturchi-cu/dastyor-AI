"""Obyektivka — voice-first bot flow (instant ack, staged progress)."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message

from config.settings import PROJECT_ROOT
from database.repositories import ai_sessions as sessions_repo
from database.repositories import users as users_repo
from features.ai.service import process_text_for_obyektivka, process_voice_for_obyektivka, oby_fill_is_acceptable
from features.bot.states import ObyektivkaStates
from features.bot.handlers.start import WELCOME
from features.obyektivka import service as oby_service
from shared.ai_errors import AI_QUOTA_USER_MSG, AiQuotaError
from shared.async_db import run as db_run
from shared.keyboards import BTN_BACK, BTN_OBY, back_menu, is_menu_button, open_oby_preview_inline, user_menu
from shared.marketing import cross_sell_cv_line, oby_intro_hook
from shared.progress import STEP_AI, STEP_AUDIO, STEP_EXTRACTED, STEP_READY, telegram_message
from shared.telegram_progress import set_step
from shared.voice import download_voice_message

logger = logging.getLogger(__name__)
router = Router()

OBY_INSTRUCTION = (
    oby_intro_hook()
    + "📌 <b>Obyektivka tayyorlash uchun quyidagi ma'lumotlarni bitta audio xabar "
    "ko'rinishida yuboring:</b>\n\n"
    "1. F.I.Sh.\n"
    "2. Tug'ilgan sana\n"
    "3. Tug'ilgan joy\n"
    "4. Millati\n"
    "5. Ma'lumoti\n"
    "6. Tamomlagan OTM\n"
    "7. Mutaxassisligi\n"
    "8. Partiyaviyligi\n"
    "9. Ilmiy darajasi\n"
    "10. Ilmiy unvoni\n"
    "11. Chet tillari\n"
    "12. Davlat mukofotlari\n"
    "13. Deputatligi\n"
    "14. Mehnat faoliyati\n"
    "15. Rasm\n"
    "16. <b>Oila a'zolari:</b>\n"
    "• ota • ona • aka • uka • opa • singil • turmush o'rtog'i\n\n"
    "Har biri uchun:\n"
    "• FISH\n"
    "• Tug'ilgan yili\n"
    "• Ish joyi\n"
    "• Lavozimi\n"
    "• Yashash manzili\n\n"
    "🎙 <b>Ovozli xabar yoki matn yuboring</b> — AI formani avtomatik to'ldiradi."
)

SAMPLE_AUDIO_PATHS = [
    PROJECT_ROOT / "assets" / "samples" / "speech.mp3",
    PROJECT_ROOT / "speech.mp3",
]


def _find_sample_audio() -> Path | None:
    for p in SAMPLE_AUDIO_PATHS:
        if p.is_file():
            return p
    return None


async def _delete_waiting_prompt(bot: Bot, state: FSMContext) -> None:
    data = await state.get_data()
    msg_id = data.get("waiting_prompt_msg_id")
    chat_id = data.get("waiting_prompt_chat_id")
    if not msg_id or not chat_id:
        return
    try:
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
    except Exception:
        pass
    await state.update_data(waiting_prompt_msg_id=None, waiting_prompt_chat_id=None)


@router.message(F.text == BTN_OBY)
async def obyektivka_start(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id if message.from_user else 0
    if uid and users_repo.is_blocked(uid):
        await message.answer("⛔ Siz bloklangansiz.")
        return
    await state.set_state(ObyektivkaStates.waiting_voice)
    await message.answer(OBY_INSTRUCTION, reply_markup=back_menu())

    sample = _find_sample_audio()
    if sample:
        asyncio.create_task(_send_sample_audio(message, sample))

    waiting_msg = await message.answer(
        "⏳ <b>Ovozli xabar yoki matn kutmoqdamiz...</b>\n"
        "Audio yozuv yoki matn ko'rinishida yuboring.",
        reply_markup=back_menu(),
    )
    await state.update_data(
        waiting_prompt_msg_id=waiting_msg.message_id,
        waiting_prompt_chat_id=waiting_msg.chat.id,
    )


async def _send_sample_audio(message: Message, sample: Path) -> None:
    try:
        await message.answer_audio(
            FSInputFile(sample),
            caption="🎧 <b>Namuna audio</b> — shu tartibda o'qib yuboring.",
        )
    except Exception as e:
        logger.warning("Sample audio send failed: %s", e)


async def _process_voice_background(
    message: Message,
    bot: Bot,
    state: FSMContext,
    status_msg: Message,
) -> None:
    uid = message.from_user.id if message.from_user else 0
    path = ""
    try:
        path = await download_voice_message(bot, message, prefix="oby_voice")
        if not path:
            await status_msg.edit_text("❌ Audio topilmadi. Qayta yuboring.")
            return

        await set_step(status_msg, STEP_AI)
        transcript, data, missing = await process_voice_for_obyektivka(path)

        if not oby_fill_is_acceptable(data):
            await status_msg.edit_text(
                "❌ Ma'lumotlarni ajratib bo'lmadi.\n"
                "Iltimos, namunadagi tartibda to'liqroq o'qib yuboring."
            )
            return

        await set_step(status_msg, STEP_EXTRACTED)

        await db_run(oby_service.save_pending, uid, data)
        await db_run(
            sessions_repo.create_session,
            uid,
            "oby_voice",
            transcript,
            data,
        )
        await state.clear()

        filled = max(10, min(95, 100 - len(missing) * 8))
        missing_text = ""
        if missing:
            labels = [m["label"] for m in missing[:6]]
            extra = len(missing) - 6
            missing_text = (
                f"\n\n⚠️ <b>Yetishmayotgan ({len(missing)}):</b>\n"
                + ", ".join(labels)
                + (f" +{extra} ta" if extra > 0 else "")
            )

        fn = data.get("fullname") or ""
        await status_msg.edit_text(
            f"{telegram_message(STEP_READY)}\n\n"
            f"<b>Obyektivka tayyorlandi!</b> (~{filled}% to'ldirildi)\n"
            f"{('👤 ' + fn) if fn else ''}"
            f"{missing_text}\n\n"
            "👇 Preview ni ko'ring va <b>Tasdiqlash</b> tugmasini bosing."
            f"{cross_sell_cv_line()}",
            reply_markup=open_oby_preview_inline(uid, missing_count=len(missing)),
        )
    except AiQuotaError:
        await status_msg.edit_text(AI_QUOTA_USER_MSG)
    except Exception as e:
        logger.exception("Obyektivka voice error: %s", e)
        await status_msg.edit_text(f"❌ Xatolik: {str(e)[:200]}")
    finally:
        if path:
            try:
                os.remove(path)
            except OSError:
                pass


@router.message(ObyektivkaStates.waiting_voice, F.voice | F.audio)
async def obyektivka_voice(message: Message, bot: Bot, state: FSMContext) -> None:
    await _delete_waiting_prompt(bot, state)
    status = await message.answer(telegram_message(STEP_AUDIO))
    asyncio.create_task(_process_voice_background(message, bot, state, status))


@router.message(ObyektivkaStates.waiting_voice, CommandStart())
@router.message(ObyektivkaStates.waiting_voice, F.text == BTN_BACK)
@router.message(ObyektivkaStates.waiting_voice, F.text.casefold() == "bekor")
async def obyektivka_back(message: Message, state: FSMContext) -> None:
    await state.clear()
    text = "Bosh menyu:"
    if message.text and message.text.startswith("/start"):
        text = WELCOME
    await message.answer(text, reply_markup=user_menu())


@router.message(ObyektivkaStates.waiting_voice, F.text)
async def obyektivka_text(message: Message, bot: Bot, state: FSMContext) -> None:
    if not message.text or message.text.startswith("/"):
        return
    if message.text == BTN_BACK or message.text.casefold() == "bekor":
        return
    if is_menu_button(message.text):
        from features.bot.handlers.start import menu_from_flow_waiting

        await menu_from_flow_waiting(message, state)
        return
    await _delete_waiting_prompt(bot, state)
    status = await message.answer("✅ Matn qabul qilindi\n⏳ AI tahlil qilmoqda...")
    uid = message.from_user.id if message.from_user else 0
    asyncio.create_task(_handle_oby_text_flow(message.text or "", status, uid, state))


async def _handle_oby_text_flow(text: str, status: Message, uid: int, state: FSMContext) -> None:
    try:
        transcript, data, missing = await process_text_for_obyektivka(text)
        if not oby_fill_is_acceptable(data):
            await status.edit_text(
                "❌ Ma'lumotlarni ajratib bo'lmadi.\n"
                "Namunadagi tartibda to'liqroq yozing."
            )
            return
        await db_run(oby_service.save_pending, uid, data)
        await db_run(sessions_repo.create_session, uid, "oby_voice", transcript, data)
        await state.clear()
        filled = max(10, min(95, 100 - len(missing) * 8))
        fn = data.get("fullname") or ""
        await status.edit_text(
            f"{telegram_message(STEP_READY, input_mode='text')}\n\n"
            f"<b>Obyektivka tayyorlandi!</b> (~{filled}% to'ldirildi)\n"
            f"{('👤 ' + fn) if fn else ''}\n\n"
            "👇 Preview ni ko'ring va tasdiqlang."
            f"{cross_sell_cv_line()}",
            reply_markup=open_oby_preview_inline(uid, missing_count=len(missing)),
        )
    except AiQuotaError:
        await status.edit_text(AI_QUOTA_USER_MSG)
    except Exception as e:
        logger.exception("Obyektivka text error: %s", e)
        await status.edit_text(f"❌ Xatolik: {str(e)[:200]}")


@router.message(ObyektivkaStates.waiting_voice)
async def obyektivka_waiting_hint(message: Message) -> None:
    await message.answer(
        "🎙 <b>Ovozli xabar</b> yoki 📝 <b>matn</b> yuboring.\n"
        "Namunadagi tartibda ma'lumotlaringizni yozing.",
        reply_markup=back_menu(),
    )

