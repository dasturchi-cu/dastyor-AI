"""Aiogram 3 — start, menu, help."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config.settings import settings
from database.repositories import users as users_repo
from features.bot.states import CvStates, ObyektivkaStates
from shared.async_db import run as db_run
from shared.marketing import cv_intro_header, welcome_message
from shared.keyboards import (
    BTN_ACCESS,
    BTN_BACK,
    BTN_CV,
    BTN_HELP,
    BTN_OBY,
    LEGACY_BTN_ACCESS,
    back_menu,
    is_access_button,
    is_credits_button,
    is_menu_button,
    open_webapp_inline,
    user_menu,
)

router = Router()

WELCOME = welcome_message()

CV_INTRO = cv_intro_header()

HELP_TEXT = (
    "ℹ️ <b>Yordam</b>\n\n"
    "/start — bosh menyu\n"
    "📄 CV — PDF resume\n"
    "✍️ Obyektivka — rasmiy Word hujjat (ovoz orqali)\n"
    "📄 Hujjat holati — kirish va to'lov holati\n"
    "🎙 Ovoz — AI avtomatik to'ldirish\n\n"
    f"Narx: <b>{settings.single_doc_price_uzs:,} so'm</b> = 1 hujjat"
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = message.from_user
    if user:
        if users_repo.is_blocked(user.id):
            await message.answer("⛔ Siz bloklangansiz.")
            return
        await db_run(
            users_repo.upsert_user,
            user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )
    await message.answer(WELCOME, reply_markup=user_menu())


@router.message(Command("help"))
@router.message(F.text == BTN_HELP)
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=user_menu())


@router.message(CvStates.waiting_input, F.text.func(is_menu_button))
@router.message(ObyektivkaStates.waiting_voice, F.text.func(is_menu_button))
async def menu_from_flow_waiting(message: Message, state: FSMContext) -> None:
    """CV/Obyektivka kutish holatida menyu tugmalari — matn to'ldirish emas."""
    await state.clear()
    text = message.text or ""
    if is_credits_button(text):
        await show_access_status(message)
    elif text == BTN_CV:
        await cv_intro(message, state)
    elif text == BTN_OBY:
        from features.bot.handlers.obyektivka import obyektivka_start

        await obyektivka_start(message, state)
    elif text == BTN_HELP:
        await cmd_help(message)
    elif text == BTN_BACK:
        await menu_back(message, state)


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


@router.message(F.text == BTN_BACK)
async def menu_back(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Bosh menyu:", reply_markup=user_menu())


@router.message(F.text == BTN_ACCESS)
@router.message(F.text.in_(LEGACY_BTN_ACCESS))
async def show_access_status(message: Message) -> None:
    uid = message.from_user.id if message.from_user else 0
    access = await db_run(users_repo.access_status, uid)
    cv = "✅ Ochiq" if access.get("has_cv_access") else "🔒 Yopiq"
    oby = "✅ Ochiq" if access.get("has_objective_access") else "🔒 Yopiq"
    await message.answer(
        f"📄 <b>Hujjat kirish holati</b>\n\n"
        f"CV: <b>{cv}</b>\n"
        f"Obyektivka: <b>{oby}</b>\n\n"
        f"ℹ️ Ovoz va matn to'ldirish — <b>bepul</b>\n"
        f"💰 Tayyor fayl: <b>{settings.single_doc_price_uzs:,} so'm</b>\n"
        f"Karta: <code>{settings.payment_card_number}</code>\n"
        f"Egasi: {settings.payment_card_owner}\n\n"
        "To'lov chekini WebApp orqali yuboring. Admin tasdiqlagach hujjat ochiladi.",
        reply_markup=user_menu(),
    )
