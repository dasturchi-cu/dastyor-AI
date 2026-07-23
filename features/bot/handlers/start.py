"""Aiogram 3 — start, menu, help."""
from __future__ import annotations

from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config.settings import settings
from database.repositories import users as users_repo
from features.bot.states import ContactStates, CvStates, ObyektivkaStates
from shared.async_db import run as db_run
from shared.keyboards import (
    BTN_BACK,
    BTN_COVER,
    BTN_CREDITS,
    BTN_CV,
    BTN_HELP,
    BTN_OBY,
    BTN_TRANSLATE,
    LEGACY_BTN_CREDITS,
    contact_admin_kb,
    is_credits_button,
    is_menu_button,
    open_webapp_inline,
    user_menu,
)
from shared.marketing import cv_intro_header, welcome_message
from shared.pricing import packages_block_text

router = Router()

WELCOME = welcome_message()

CV_INTRO = cv_intro_header()

HELP_TEXT = (
    "ℹ️ <b>Yordam</b>\n\n"
    "/start — bosh menyu\n"
    "/cv — PDF resume\n"
    "/obyektivka — rasmiy Word hujjat\n"
    "/cover — AI Muqova xati (Cover Letter) yozish\n"
    "/translate — Hujjatni boshqa tilga tarjima qilish\n"
    "/balance — to'langan mablag' va hujjatlar\n"
    "/contact — admin bilan bog'lanish\n"
    "/help — yordam\n\n"
    "🎙 Ovoz yoki matn — AI avtomatik to'ldirish (bepul)\n"
    "📄 Demo (belgili) bepul · 💎 Toza fayl — paket\n\n"
    f"{packages_block_text()}"
)


def _contact_text() -> str:
    admin = settings.support_admin_username.lstrip("@")
    return (
        "📞 <b>Bog'lanish</b>\n\n"
        f"Savol yoki muammo bo'lsa, <a href=\"https://t.me/{admin}\">@{admin}</a> ga yozing.\n\n"
        "Yoki shu chatga oddiy xabar yozing — operatorlarga yetkazamiz."
    )


async def _blocked_reply(message: Message) -> bool:
    uid = message.from_user.id if message.from_user else 0
    if uid and users_repo.is_blocked(uid):
        await message.answer("⛔ Siz bloklangansiz.")
        return True
    return False


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = message.from_user
    if not user:
        return
    if users_repo.is_blocked(user.id):
        await message.answer("⛔ Siz bloklangansiz.")
        return

    ref_id = None
    if message.text and len(message.text.split()) > 1:
        arg = message.text.split()[1]
        if arg.startswith("ref_"):
            try:
                ref_id = int(arg.replace("ref_", ""))
            except ValueError:
                pass

    is_new = not users_repo.get_by_telegram_id(user.id)

    await db_run(
        users_repo.upsert_user,
        user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        referred_by_id=ref_id if (ref_id and ref_id != user.id and is_new) else None,
    )
    if ref_id and ref_id != user.id and not is_new:
        await db_run(users_repo.attach_referrer_if_empty, user.id, ref_id)

    await message.answer(WELCOME, reply_markup=user_menu(user.id))


@router.message(Command("help"))
@router.message(F.text == BTN_HELP)
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=user_menu(message.from_user.id if message.from_user else None))


@router.message(Command("cv"))
async def cmd_cv(message: Message, state: FSMContext) -> None:
    if await _blocked_reply(message):
        return
    await state.clear()
    await cv_intro(message, state)


@router.message(Command("obyektivka"))
async def cmd_obyektivka(message: Message, state: FSMContext) -> None:
    if await _blocked_reply(message):
        return
    await state.clear()
    from features.bot.handlers.obyektivka import obyektivka_start

    await obyektivka_start(message, state)


@router.message(Command("balance"))
async def cmd_balance(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_credits(message)


@router.message(Command("contact"))
async def cmd_contact(message: Message, state: FSMContext) -> None:
    await state.set_state(ContactStates.waiting_message)
    admin = settings.support_admin_username
    await message.answer(
        _contact_text(),
        reply_markup=contact_admin_kb(admin),
    )


@router.message(ContactStates.waiting_message, F.text.func(is_menu_button))
async def menu_from_contact(message: Message, state: FSMContext) -> None:
    await state.clear()
    text = message.text or ""
    if is_credits_button(text):
        await show_credits(message)
    elif text == BTN_CV:
        await cv_intro(message, state)
    elif text == BTN_OBY:
        from features.bot.handlers.obyektivka import obyektivka_start

        await obyektivka_start(message, state)
    elif text == BTN_COVER:
        from features.bot.handlers.cover_letter import cmd_cover

        await cmd_cover(message, state)
    elif text == BTN_TRANSLATE:
        from features.bot.handlers.translate import cmd_translate

        await cmd_translate(message)
    elif text == BTN_HELP:
        await cmd_help(message)
    elif text == BTN_BACK:
        await menu_back(message, state)


@router.message(CvStates.waiting_input, F.text.func(is_menu_button))
@router.message(ObyektivkaStates.waiting_voice, F.text.func(is_menu_button))
async def menu_from_flow_waiting(message: Message, state: FSMContext) -> None:
    """CV/Obyektivka kutish holatida menyu tugmalari — matn to'ldirish emas."""
    await state.clear()
    text = message.text or ""
    if is_credits_button(text):
        await show_credits(message)
    elif text == BTN_CV:
        await cv_intro(message, state)
    elif text == BTN_OBY:
        from features.bot.handlers.obyektivka import obyektivka_start

        await obyektivka_start(message, state)
    elif text == BTN_COVER:
        from features.bot.handlers.cover_letter import cmd_cover

        await cmd_cover(message, state)
    elif text == BTN_TRANSLATE:
        from features.bot.handlers.translate import cmd_translate

        await cmd_translate(message)
    elif text == BTN_HELP:
        await cmd_help(message)
    elif text == BTN_BACK:
        await menu_back(message, state)


def _find_cv_sample_audio() -> Path | None:
    from config.settings import PROJECT_ROOT
    for filename in ("cv_speech.mp3", "cv_speech.ogg", "cv_speech.wav"):
        for folder in (PROJECT_ROOT / "assets" / "samples", PROJECT_ROOT):
            p = folder / filename
            if p.is_file():
                return p
    return None


@router.message(F.text == BTN_CV)
async def cv_intro(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id if message.from_user else 0
    if uid and users_repo.is_blocked(uid):
        await message.answer("⛔ Siz bloklangansiz.")
        return
    from features.bot.handlers.voice import CV_INSTRUCTION
    await state.set_state(CvStates.waiting_input)
    await message.answer(
        f"{CV_INTRO}\n\n{CV_INSTRUCTION}",
        reply_markup=open_webapp_inline(uid, "cv"),
    )

    from features.bot.handlers.obyektivka import _send_sample_audio
    sample = _find_cv_sample_audio()
    if sample:
        import asyncio
        asyncio.create_task(_send_sample_audio(message, sample))


@router.message(F.text == BTN_COVER)
async def cover_from_menu(message: Message, state: FSMContext) -> None:
    if await _blocked_reply(message):
        return
    from features.bot.handlers.cover_letter import cmd_cover

    await cmd_cover(message, state)


@router.message(F.text == BTN_TRANSLATE)
async def translate_from_menu(message: Message) -> None:
    if await _blocked_reply(message):
        return
    from features.bot.handlers.translate import cmd_translate

    await cmd_translate(message)


@router.message(F.text == BTN_BACK)
async def menu_back(message: Message, state: FSMContext) -> None:
    await state.clear()
    uid = message.from_user.id if message.from_user else None
    await message.answer("Bosh menyu:", reply_markup=user_menu(uid))


async def show_credits_for_uid(message: Message, uid: int) -> None:
    status = await db_run(users_repo.get_credits, uid)
    progress = await db_run(users_repo.get_referral_progress, uid)
    promo = await db_run(users_repo.ensure_pay_promo, uid)
    bot_username = settings.bot_username or "DastyorAiBot"
    ref_link = f"https://t.me/{bot_username}?start=ref_{uid}"
    from shared.keyboards import payment_choice_keyboard
    from shared.pricing import packages_block_text
    from shared.referral import referral_balance_block

    promo_line = ""
    if promo.get("active"):
        h = int(promo.get("hours_left") or 0)
        promo_line = f"\n⚡️ {h} soat ichida to'lasangiz: +1 Muqova bepul\n"

    await message.answer(
        f"💳 <b>Qolgan yuklashlar:</b> {status} ta\n"
        f"Har bir toza fayl = 1 yuklash.\n"
        f"{promo_line}\n"
        f"{packages_block_text()}\n"
        f"Karta: <code>{settings.payment_card_number}</code>\n"
        f"Egasi: {settings.payment_card_owner}\n\n"
        f"{referral_balance_block(ref_link, progress)}",
        reply_markup=payment_choice_keyboard(uid),
    )


@router.message(F.text == BTN_CREDITS)
@router.message(F.text.in_(LEGACY_BTN_CREDITS))
async def show_credits(message: Message) -> None:
    uid = message.from_user.id if message.from_user else 0
    await show_credits_for_uid(message, uid)
