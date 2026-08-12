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
from shared.ai_errors import AI_QUOTA_USER_MSG, AiQuotaError, translate_error_to_user_message
from shared.async_db import run as db_run
from shared.keyboards import (
    BTN_BACK,
    BTN_OBY,
    back_menu,
    btn_filter,
    is_btn_match,
    is_menu_button,
    open_oby_preview_inline,
    open_webapp_inline,
    user_menu,
)
from shared.marketing import cross_sell_cover_line, cross_sell_cv_line, cross_sell_translate_line, oby_intro_hook
from shared.progress import STEP_AI, STEP_AUDIO, STEP_EXTRACTED, STEP_READY, telegram_message
from shared.telegram_progress import set_step
from shared.voice import download_voice_message

logger = logging.getLogger(__name__)
router = Router()

OBY_EXAMPLE_TEMPLATE = (
    "\n\n💡 <b>Nusxa ko'chirib, o'z ma'lumotlaringizni yozib yuborishingiz mumkin bo'lgan namuna:</b>\n"
    "<blockquote expandable>"
    "Ism: Karimov Jasur Alisherovich\n"
    "Tug'ilgan sana: 1995-yil 12-may\n"
    "Tug'ilgan joy: Toshkent shahri\n"
    "Millati: O'zbek\n"
    "Ma'lumoti: Oliy\n"
    "OTM: Toshkent axborot texnologiyalari universiteti, 2017-yilda tamomlagan\n"
    "Mutaxassisligi: Dasturiy injiniring\n"
    "Tillar: Rus tili, Ingliz tili\n"
    "Mehnat faoliyati:\n"
    "2017-2020 EPAM Systems dasturchisi\n"
    "2020-hozirgi vaqt Dastyor AI yetakchi dasturchisi\n\n"
    "Oilam:\n"
    "Otam: Karimov Alisher, 1968-yil, nafaqaxo'r, yashash joyi Toshkent shahri\n"
    "Onam: Karimova Ra'no, 1972-yil, o'qituvchi, yashash joyi Toshkent shahri"
    "</blockquote>"
)


OBY_INSTRUCTION = (
    oby_intro_hook()
    + "📌 <b>F.I.Sh., tug'ilgan sana, ma'lumoti, mehnat faoliyati, oila a'zolari</b> "
    "— yozing yoki ovoz yuboring."
    f"{OBY_EXAMPLE_TEMPLATE}"
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


AI_FLOW_TIMEOUT_SECONDS = 50


async def _finish_status(status: Message, text: str, **kwargs) -> None:
    """Deliver the final status update, guaranteeing the user gets *something*.

    If editing the status message fails (deleted, rate-limited, stale), fall
    back to a fresh message instead of letting the background task die with
    the user stuck on "AI tahlil qilmoqda..." forever.
    """
    try:
        await status.edit_text(text, **kwargs)
    except Exception:
        try:
            await status.answer(text, **kwargs)
        except Exception:
            logger.exception("Failed to deliver final obyektivka status to user")


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


async def _auto_delete_waiting_prompt_after_delay(
    bot: Bot, state: FSMContext, chat_id: int, message_id: int, delay: int = 60
) -> None:
    await asyncio.sleep(delay)
    try:
        data = await state.get_data()
        current_msg_id = data.get("waiting_prompt_msg_id")
        if current_msg_id == message_id:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception:
                pass
            await state.update_data(waiting_prompt_msg_id=None, waiting_prompt_chat_id=None)
    except Exception:
        pass


@router.message(F.text == BTN_OBY)
async def obyektivka_start(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id if message.from_user else 0
    if uid and users_repo.is_blocked(uid):
        await message.answer("⛔ Siz bloklangansiz.", reply_markup=user_menu(uid))
        return
    await state.set_state(ObyektivkaStates.waiting_voice)
    await message.answer(OBY_INSTRUCTION, reply_markup=open_webapp_inline(uid, "obyektivka"))

    sample = _find_sample_audio()
    if sample:
        asyncio.create_task(_send_sample_audio(message, sample))

    waiting_msg = await message.answer(
        "⏳ <b>Ovozli xabar yoki matn kutmoqdamiz...</b>\n"
        "Audio yozuv yoki matn ko'rinishida yuboring.",
        reply_markup=user_menu(uid),
    )
    await state.update_data(
        waiting_prompt_msg_id=waiting_msg.message_id,
        waiting_prompt_chat_id=waiting_msg.chat.id,
    )
    if message.bot:
        asyncio.create_task(
            _auto_delete_waiting_prompt_after_delay(
                message.bot, state, waiting_msg.chat.id, waiting_msg.message_id
            )
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
            await _finish_status(status_msg, "❌ Audio topilmadi. Qayta yuboring.")
            return

        await set_step(status_msg, STEP_AI)
        transcript, data, missing = await asyncio.wait_for(
            process_voice_for_obyektivka(path), timeout=AI_FLOW_TIMEOUT_SECONDS
        )

        if not oby_fill_is_acceptable(data):
            if data:
                await db_run(oby_service.save_pending, uid, data)
            await _finish_status(
                status_msg,
                "ℹ️ <b>Ma'lumotlar kamlik qilmoqda.</b>\n\n"
                "Lekin xavotirlanmang! Quyidagi tugmani bosib, formani WebApp orqali o'zingiz to'ldirishingiz mumkin 👇",
                reply_markup=open_webapp_inline(uid, "obyektivka")
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
        await _finish_status(
            status_msg,
            f"{telegram_message(STEP_READY)}\n\n"
            f"<b>Obyektivka tayyorlandi!</b> (~{filled}% to'ldirildi)\n"
            f"{('👤 ' + fn) if fn else ''}"
            f"{missing_text}\n\n"
            "👇 Preview ni ko'ring va <b>Tasdiqlash</b> tugmasini bosing."
            f"{cross_sell_cv_line()}{cross_sell_cover_line()}{cross_sell_translate_line()}",
            reply_markup=open_oby_preview_inline(uid, missing_count=len(missing)),
        )
    except AiQuotaError:
        await _finish_status(status_msg, AI_QUOTA_USER_MSG)
    except Exception as e:
        logger.exception("Obyektivka voice error: %s", e)
        await _finish_status(status_msg, translate_error_to_user_message(e))
    finally:
        if path:
            try:
                os.remove(path)
            except OSError:
                pass


from shared.premium_emoji import safe_react


@router.message(ObyektivkaStates.waiting_voice, F.voice)
@router.message(ObyektivkaStates.waiting_voice, F.audio)
async def obyektivka_voice(message: Message, bot: Bot, state: FSMContext) -> None:
    uid = message.from_user.id if message.from_user else 0
    await safe_react(message, "🎙")
    await _delete_waiting_prompt(bot, state)
    status = await message.answer(telegram_message(STEP_AUDIO), reply_markup=user_menu(uid))
    asyncio.create_task(_process_voice_background(message, bot, state, status))


@router.message(ObyektivkaStates.waiting_voice, CommandStart())
@router.message(ObyektivkaStates.waiting_voice, btn_filter(BTN_BACK))
@router.message(ObyektivkaStates.waiting_voice, F.text.casefold() == "bekor")
async def obyektivka_back(message: Message, state: FSMContext) -> None:
    await state.clear()
    text = "Bosh menyu:"
    if message.text and message.text.startswith("/start"):
        text = WELCOME
    uid = message.from_user.id if message.from_user else None
    await message.answer(text, reply_markup=user_menu(uid))


@router.message(ObyektivkaStates.waiting_voice, F.text, ~F.text.startswith("/"))
async def obyektivka_text(message: Message, bot: Bot, state: FSMContext) -> None:
    if not message.text:
        return
    if is_btn_match(message.text, BTN_BACK) or message.text.casefold() == "bekor":
        return
    if is_menu_button(message.text):
        from features.bot.handlers.start import menu_from_flow_waiting

        await menu_from_flow_waiting(message, state)
        return
    await safe_react(message, "✍️")
    await _delete_waiting_prompt(bot, state)
    uid = message.from_user.id if message.from_user else 0
    status = await message.answer(telegram_message(STEP_AI, input_mode="text"), reply_markup=user_menu(uid))
    asyncio.create_task(_handle_oby_text_flow(message.text or "", status, uid, state))


async def _handle_oby_text_flow(text: str, status: Message, uid: int, state: FSMContext) -> None:
    try:
        transcript, data, missing = await asyncio.wait_for(
            process_text_for_obyektivka(text), timeout=AI_FLOW_TIMEOUT_SECONDS
        )
        await _finish_status(status, telegram_message(STEP_EXTRACTED, input_mode="text"))
        if not oby_fill_is_acceptable(data):
            if data:
                await db_run(oby_service.save_pending, uid, data)
            await _finish_status(
                status,
                "ℹ️ <b>Ma'lumotlar kamlik qilmoqda.</b>\n\n"
                "Lekin xavotirlanmang! Quyidagi tugmani bosib, formani WebApp orqali o'zingiz to'ldirishingiz mumkin 👇",
                reply_markup=open_webapp_inline(uid, "obyektivka")
            )
            return
        await db_run(oby_service.save_pending, uid, data)
        await db_run(sessions_repo.create_session, uid, "oby_voice", transcript, data)
        await state.clear()
        filled = max(10, min(95, 100 - len(missing) * 8))
        fn = data.get("fullname") or ""
        await _finish_status(
            status,
            f"{telegram_message(STEP_READY, input_mode='text')}\n\n"
            f"<b>Obyektivka tayyorlandi!</b> (~{filled}% to'ldirildi)\n"
            f"{('👤 ' + fn) if fn else ''}\n\n"
            "👇 Preview ni ko'ring va tasdiqlang."
            f"{cross_sell_cv_line()}{cross_sell_cover_line()}{cross_sell_translate_line()}",
            reply_markup=open_oby_preview_inline(uid, missing_count=len(missing)),
        )
    except AiQuotaError:
        await _finish_status(status, AI_QUOTA_USER_MSG)
    except Exception as e:
        logger.exception("Obyektivka text error: %s", e)
        await _finish_status(status, translate_error_to_user_message(e))


@router.message(ObyektivkaStates.waiting_voice)
async def obyektivka_waiting_hint(message: Message) -> None:
    uid = message.from_user.id if message.from_user else 0
    await message.answer(
        "🎙 <b>Ovozli xabar</b> yoki 📝 <b>matn</b> yuboring.\n"
        "Namunadagi tartibda ma'lumotlaringizni yozing.",
        reply_markup=user_menu(uid),
    )

