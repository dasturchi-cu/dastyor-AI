"""Aiogram 3 — start, menu, help."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config.settings import settings
from database.repositories import users as users_repo
from features.bot.states import ContactStates, CvStates, ObyektivkaStates
from shared.async_db import run as db_run
from shared.marketing import cv_intro_header, welcome_message
from shared.keyboards import (
    BTN_BACK,
    BTN_CREDITS,
    BTN_CV,
    BTN_HELP,
    BTN_OBY,
    LEGACY_BTN_CREDITS,
    contact_admin_kb,
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
    "/cv — PDF resume\n"
    "/obyektivka — rasmiy Word hujjat\n"
    "/cover — AI Muqova xati (Cover Letter) yozish\n"
    "/translate — Hujjatni boshqa tilga tarjima qilish\n"
    "/balance — to'langan mablag' va hujjatlar\n"
    "/contact — admin bilan bog'lanish\n"
    "/help — yordam\n\n"
    "🎙 Ovoz yoki matn — AI avtomatik to'ldirish (bepul)\n\n"
    f"Narx: <b>{settings.single_doc_price_uzs:,} so'm</b> = 1 hujjat"
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

    from features.bot.handlers.obyektivka import _find_sample_audio, _send_sample_audio
    sample = _find_sample_audio()
    if sample:
        import asyncio
        asyncio.create_task(_send_sample_audio(message, sample))


@router.message(F.text == BTN_BACK)
async def menu_back(message: Message, state: FSMContext) -> None:
    await state.clear()
    uid = message.from_user.id if message.from_user else None
    await message.answer("Bosh menyu:", reply_markup=user_menu(uid))


@router.message(F.text == BTN_CREDITS)
@router.message(F.text.in_(LEGACY_BTN_CREDITS))
async def show_credits(message: Message) -> None:
    uid = message.from_user.id if message.from_user else 0
    status = await db_run(users_repo.get_credits, uid)
    ref_count = await db_run(users_repo.get_referral_count, uid)
    bot_username = settings.bot_username or "DastyorAiBot"
    ref_link = f"https://t.me/{bot_username}?start=ref_{uid}"
    from shared.keyboards import payment_choice_keyboard
    await message.answer(
        f"💳 <b>Sotib olingan yuklashlar:</b> {status} ta\n"
        f"ℹ️ Ovoz va matn to'ldirish — <b>bepul</b>\n"
        f"💰 1 ta yuklash narxi: <b>7,999 so'm</b>\n"
        f"Karta: <code>{settings.payment_card_number}</code>\n"
        f"Egasi: {settings.payment_card_owner}\n\n"
        f"💡 <b>Eslatma:</b> Yuklash balansi universaldir! Sotib olgan yuklash limitlaringizdan CV, Obyektivka, Muqova xati (Cover letter) yoki Hujjat tarjima qilish xizmatlarining istalganida foydalanishingiz mumkin.\n\n"
        f"👥 <b>Siz taklif qilgan faol do'stlaringiz:</b> {ref_count} ta\n"
        f"🎁 <b>Bepul yuklash olish:</b> Do'stlaringizga taklif havolangizni ulashing. Har 3 ta do'stingiz botdan foydalanib o'zining birinchi bepul hujjatini yuklab olganida sizga +1 ta bepul yuklash sovg'a qilinadi!\n"
        f"Havolangiz:\n<code>{ref_link}</code>",
        reply_markup=payment_choice_keyboard(uid),
    )
