"""Aiogram 3 — start, menu, help."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config.settings import settings
from database.repositories import users as users_repo
from shared.keyboards import (
    BTN_BACK,
    BTN_CREDITS,
    BTN_CV,
    BTN_HELP,
    BTN_OBY,
    back_menu,
    open_webapp_inline,
    user_menu,
)

router = Router()

WELCOME = (
    "👋 <b>HUJJATCHI AI</b> ga xush kelibsiz!\n\n"
    "📄 <b>CV</b> — forma yoki ovoz → <b>PDF</b>\n"
    "✍️ <b>Obyektivka</b> — ovoz yuboring → AI to'ldiradi → <b>Word (.docx)</b>\n\n"
    "💳 Har bir tasdiqlangan to'lov = <b>1 kredit</b> = <b>1 ta hujjat</b> (CV yoki Obyektivka).\n"
    "🎙 Ovoz yuboring — AI forma maydonlarini avtomatik to'ldiradi.\n\n"
    "👇 Xizmatni tanlang."
)

CV_INTRO = (
    "📄 <b>CV Resume</b>\n\n"
    "• Forma orqali to'ldiring yoki ovoz yuboring\n"
    "• AI ma'lumotlarni ajratadi va formani to'ldiradi\n"
    "• Shablon: Modern / Classic / Corporate\n"
    "• Natija: <b>PDF</b> (ATS-friendly)\n\n"
    "Formani oching yoki ovozli xabar yuboring."
)

HELP_TEXT = (
    "ℹ️ <b>Yordam</b>\n\n"
    "/start — bosh menyu\n"
    "📄 CV — PDF resume\n"
    "✍️ Obyektivka — rasmiy Word hujjat (ovoz orqali)\n"
    "💳 Kreditlar — balans va to'lov\n"
    "🎙 Ovoz — AI avtomatik to'ldirish\n\n"
    f"Narx: <b>{settings.single_doc_price_uzs:,} so'm</b> = 1 hujjat"
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = message.from_user
    if user:
        users_repo.upsert_user(
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


@router.message(F.text == BTN_CV)
async def cv_intro(message: Message) -> None:
    uid = message.from_user.id if message.from_user else 0
    await message.answer(CV_INTRO, reply_markup=open_webapp_inline(uid, "cv"))


@router.message(F.text == BTN_BACK)
async def menu_back(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Bosh menyu:", reply_markup=user_menu())


@router.message(F.text == BTN_CREDITS)
async def show_credits(message: Message) -> None:
    uid = message.from_user.id if message.from_user else 0
    status = users_repo.get_credits(uid)
    await message.answer(
        f"💳 <b>Kreditlar:</b> {status}\n"
        f"ℹ️ 1 kredit = 1 ta hujjat (<b>CV yoki Obyektivka</b>)\n"
        f"💰 Narx: {settings.single_doc_price_uzs:,} so'm = 1 kredit\n"
        f"Karta: <code>{settings.payment_card_number}</code>\n"
        f"Egasi: {settings.payment_card_owner}\n\n"
        "To'lov chekini WebApp orqali yuboring.",
        reply_markup=user_menu(),
    )
