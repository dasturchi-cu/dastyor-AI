"""CV / Obyektivka: avval tushuntirish, keyin forma (WebApp)."""
from __future__ import annotations

import asyncio
import logging
import os

from telegram import Message, Update
from telegram.constants import ChatAction
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from bot.constants.states import WaitingState
from bot.ui.keyboards import (
    cv_button_labels,
    oby_button_labels,
    service_open_inline,
    user_reply_menu,
)
from bot.ui.messages import (
    CV_INSTRUCTION_TEXT,
    CV_INTRO_TEXT,
    OBY_INSTRUCTION_TEXT,
    OBY_INTRO_TEXT,
)

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HANDLERS_DIR = os.path.dirname(os.path.abspath(__file__))


def _uid(update: Update) -> int:
    return int(update.effective_user.id) if update.effective_user else 0


def _webapp_base(context: ContextTypes.DEFAULT_TYPE) -> str:
    base = (context.bot_data.get("webapp_base") or "").strip()
    if base.startswith("https://"):
        return base
    try:
        from config import resolve_webapp_base

        return resolve_webapp_base()
    except Exception:
        return base


def _reply_target(update: Update) -> Message | None:
    if update.message:
        return update.message
    if update.callback_query and update.callback_query.message:
        return update.callback_query.message
    return None


def is_cv_button(text: str) -> bool:
    return (text or "").strip() in cv_button_labels()


def is_oby_button(text: str) -> bool:
    return (text or "").strip() in oby_button_labels()


def _oby_sample_audio_paths() -> list[str]:
    return [
        os.path.join(BASE_DIR, "speech.mp3"),
        os.path.join(HANDLERS_DIR, "speech (1).mp3"),
        os.path.join(HANDLERS_DIR, "namuna.mp3"),
        os.path.join(BASE_DIR, "namuna.mp3"),
    ]


def _oby_sample_audio_enabled() -> bool:
    return os.getenv("OBY_SAMPLE_AUDIO", "1").strip().lower() not in ("0", "false", "no")


def _find_oby_sample_audio_path() -> str | None:
    for path in _oby_sample_audio_paths():
        if path and os.path.isfile(path):
            return path
    return None


async def _send_oby_sample_audio(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Namuna ovoz — matndan keyin (UPLOAD_VOICE yo‘q, chat qotmaydi)."""
    if not _oby_sample_audio_enabled():
        return
    path = _find_oby_sample_audio_path()
    if not path:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="🎙 <b>Namuna audio</b> hozir yo‘q. Formani oching yoki o‘zingiz ovoz yuboring.",
                parse_mode="HTML",
            )
        except Exception:
            pass
        return
    try:
        from telegram import InputFile

        async def _upload():
            return await context.bot.send_audio(
                chat_id=chat_id,
                audio=InputFile(path),
                caption="🎙 <b>Namuna</b> — shu tartibda o‘qib yuboring",
                parse_mode="HTML",
                title="Obyektivka namuna",
            )

        await asyncio.wait_for(_upload(), timeout=25.0)
    except asyncio.TimeoutError:
        logger.warning("sample audio send timeout path=%s", path)
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="🎙 Namuna audio yuklanmadi. Forma yoki ovoz yuboring.",
            )
        except Exception:
            pass
    except Exception as e:
        logger.warning("sample audio send failed path=%s: %s", path, e)


async def _reply_cv_intro(message: Message, base: str, uid: int, text: str | None = None) -> None:
    markup = service_open_inline(base, uid, "cv")
    body = text or CV_INTRO_TEXT
    try:
        await message.reply_text(body, parse_mode="HTML", reply_markup=markup)
    except BadRequest as e:
        logger.warning("CV intro reply failed (markup): %s", e)
        await message.reply_text(
            body + "\n\n⚠️ <i>Forma tugmasi vaqtincha ishlamadi — /start yoki admin bilan bog‘laning.</i>",
            parse_mode="HTML",
        )


async def send_cv_intro(message: Message, context: ContextTypes.DEFAULT_TYPE, uid: int) -> None:
    context.user_data.pop("waiting_for", None)
    base = _webapp_base(context)
    context.bot_data["webapp_base"] = base
    await _reply_cv_intro(message, base, uid, CV_INSTRUCTION_TEXT)
    try:
        from bot.services.bot_analytics import log_bot_event

        asyncio.create_task(asyncio.to_thread(log_bot_event, uid, "bot_cv_intro_open"))
    except Exception:
        pass


async def send_obyektivka_intro(message: Message, context: ContextTypes.DEFAULT_TYPE, uid: int) -> None:
    context.user_data["waiting_for"] = WaitingState.OBYEKTIVKA_AUDIO
    base = _webapp_base(context)
    context.bot_data["webapp_base"] = base
    inline = service_open_inline(base, uid, "obyektivka")
    combined = OBY_INSTRUCTION_TEXT

    try:
        await message.reply_text(combined, parse_mode="HTML", reply_markup=inline)
    except BadRequest as e:
        logger.warning("Obyektivka intro reply failed (markup): %s", e)
        try:
            await message.reply_text(combined, parse_mode="HTML")
        except Exception as e2:
            logger.error("Obyektivka intro plain reply failed: %s", e2, exc_info=True)
            url = None
            try:
                from bot.ui.keyboards import webapp_service_url

                url = webapp_service_url(base, uid, "obyektivka")
            except Exception:
                pass
            tail = f"\n\n🔗 {url}" if url else ""
            await message.reply_text("✍️ Obyektivka" + tail)

    chat_id = message.chat_id
    if chat_id and _oby_sample_audio_enabled():
        await _send_oby_sample_audio(context, chat_id)

    try:
        from bot.services.bot_analytics import log_bot_event

        asyncio.create_task(asyncio.to_thread(log_bot_event, uid, "bot_oby_intro_open"))
    except Exception:
        pass


async def handle_cv_intro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = _reply_target(update)
    if not msg:
        return
    await send_cv_intro(msg, context, _uid(update))


async def handle_obyektivka_intro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = _reply_target(update)
    if not msg:
        return
    try:
        await send_obyektivka_intro(msg, context, _uid(update))
    except Exception as e:
        logger.error("handle_obyektivka_intro: %s", e, exc_info=True)
        try:
            await msg.reply_text(
                "❌ Obyektivka ochilmadi. /start bosing yoki bir ozdan keyin qayta urinib ko‘ring.",
            )
        except Exception:
            pass


async def intro_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    await q.answer()
    data = (q.data or "").strip()
    msg = q.message
    if not msg:
        return
    if data == "intro_cv":
        await send_cv_intro(msg, context, _uid(update))
        return
    if data == "intro_oby":
        await send_obyektivka_intro(msg, context, _uid(update))
        return
    if data == "intro_help":
        from bot.ui.messages import HELP_TEXT

        await msg.reply_text(
            HELP_TEXT,
            parse_mode="HTML",
            reply_markup=user_reply_menu(context.bot_data.get("webapp_base", ""), _uid(update)),
        )
        return
    if data == "intro_contact":
        from bot.handlers.feedback import start_feedback

        await start_feedback(update, context)
        return
    if data == "intro_my_docs":
        from bot.handlers.my_documents import send_my_documents

        await send_my_documents(msg, context, _uid(update))
        return
    if data == "menu_back":
        await handle_menu_back_from_callback(update, context)


async def handle_menu_back_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from bot.ui.messages import WELCOME_TEXT

    q = update.callback_query
    if not q or not q.message:
        return
    context.user_data.pop("waiting_for", None)
    await q.message.reply_text(
        WELCOME_TEXT,
        parse_mode="HTML",
        reply_markup=user_reply_menu(context.bot_data.get("webapp_base", ""), _uid(update)),
    )


async def handle_menu_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from bot.ui.messages import WELCOME_TEXT

    if not update.message:
        return
    context.user_data.pop("waiting_for", None)
    uid = _uid(update)
    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode="HTML",
        reply_markup=user_reply_menu(context.bot_data.get("webapp_base", ""), uid),
    )
