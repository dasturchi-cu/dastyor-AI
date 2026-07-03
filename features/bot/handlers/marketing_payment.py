"""Marketing & direct in-bot payments handler."""
from __future__ import annotations

import logging
import uuid
import asyncio
from pathlib import Path
from typing import Any

from aiogram import F, Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from config.settings import PROJECT_ROOT, settings
from database.repositories import users as users_repo
from database.repositories import payments as payments_repo
from features.bot.states import PaymentStates
from shared.async_db import run as db_run
from shared.keyboards import (
    BTN_BACK,
    BTN_COVER,
    BTN_CV,
    BTN_HELP,
    BTN_OBY,
    BTN_SAMPLES,
    BTN_TRANSLATE,
    is_credits_button,
    is_menu_button,
    user_menu,
)
from shared.marketing import format_price_uzs
from features.payment.router import _finalize_payment_submission

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == BTN_SAMPLES)
async def show_samples(message: Message) -> None:
    uid = message.from_user.id if message.from_user else 0
    if uid and users_repo.is_blocked(uid):
        await message.answer("⛔ Siz bloklangansiz.")
        return

    # Send CV sample
    cv_path = PROJECT_ROOT / "assets" / "samples" / "cv_sample_v2.png"
    if cv_path.is_file():
        await message.answer_photo(
            FSInputFile(cv_path),
            caption=(
                "📄 <b>CV (Resume) shablonimiz namunasi</b>\n\n"
                "🎨 Bu — bitta misol xolos! Botimizda <b>shunga o'xshash 8 ta turli dizayn</b> mavjud.\n"
                "Har biri zamonaviy, professional va ish beruvchilar diqqatini tortadigan.\n\n"
                "✅ Siz CV yaratishda <b>o'zingizga yoqqan dizaynni</b> tanlay olasiz."
            ),
            parse_mode="HTML",
        )
    else:
        logger.warning("CV sample file not found at %s", cv_path)

    # Send Obyektivka sample
    oby_path = PROJECT_ROOT / "assets" / "samples" / "oby_sample_v2.png"
    if oby_path.is_file():
        await message.answer_photo(
            FSInputFile(oby_path),
            caption=(
                "✍️ <b>Obyektivka (Ma'lumotnoma) namunasi</b>\n\n"
                "📋 Davlat va xususiy tashkilotlar standarti asosida tayyorlanadigan rasmiy format.\n\n"
                "💡 <i>«Obyektivka yaratish» tugmasini bosing — bot sizdan ma'lumotlarni so'raydi va avtomatik rasmiy hujjat tayyorlab beradi!</i>"
            ),
            parse_mode="HTML",
        )
    else:
        logger.warning("Obyektivka sample file not found at %s", oby_path)


@router.callback_query(F.data == "pay_via_bot")
async def choose_payment_type(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "❓ <b>Qaysi xizmat uchun to'lov qilmoqchisiz?</b>\n\n"
        "💡 <i>Eslatma: Qaysi birini tanlasangiz ham, sotib olingan yuklash limiti universaldir — CV, Obyektivka, Muqova xati va Tarjima xizmatlarining barchasiga birdek amal qiladi.</i>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📄 CV Resume uchun", callback_data="pay_bot_type_cv"),
                ],
                [
                    InlineKeyboardButton(text="✍️ Obyektivka uchun", callback_data="pay_bot_type_oby"),
                ],
                [
                    InlineKeyboardButton(text="📝 Muqova xati uchun", callback_data="pay_bot_type_cover"),
                ],
                [
                    InlineKeyboardButton(text="🌐 Hujjatni tarjima qilish uchun", callback_data="pay_bot_type_translate"),
                ],
                [
                    InlineKeyboardButton(text="❌ Orqaga", callback_data="pay_cancel"),
                ]
            ]
        )
    )


@router.callback_query(F.data.startswith("pay_bot_type_"))
async def start_bot_payment(callback: CallbackQuery, state: FSMContext) -> None:
    kind_raw = callback.data.replace("pay_bot_type_", "")
    if kind_raw not in ("cv", "oby", "cover", "translate"):
        await callback.answer("Noto'g'ri tanlov", show_alert=True)
        return

    document_type = "obyektivka" if kind_raw == "oby" else kind_raw
    labels = {
        "cv": "CV Resume",
        "obyektivka": "Obyektivka",
        "cover": "Muqova xati",
        "translate": "Hujjat tarjimasi",
    }
    label = labels[document_type]
    price = format_price_uzs()

    await state.set_state(PaymentStates.waiting_screenshot)
    await state.update_data(payment_document_type=document_type, payment_label=label)

    await callback.message.edit_text(
        f"💳 <b>{label} to'lovi ({price} so'm)</b>\n\n"
        f"Karta: <code>{settings.payment_card_number}</code>\n"
        f"Egasi: <b>{settings.payment_card_owner}</b>\n\n"
        f"Iltimos, to'lovni amalga oshirgach, to'lov cheki rasm/skrinshotini shu yerga yuboring 👇\n\n"
        "ℹ️ Chek kutishda ham 💳 Pul balansi yoki boshqa menyu tugmalaridan foydalanishingiz mumkin.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="pay_cancel")]
            ]
        ),
    )


@router.callback_query(F.data == "pay_cancel")
async def cancel_bot_payment(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    document_type = data.get("payment_document_type")
    await state.clear()
    uid = callback.from_user.id
    status = await db_run(users_repo.get_credits, uid)
    progress = await db_run(users_repo.get_referral_progress, uid)
    bot_username = settings.bot_username or "DastyorAiBot"
    ref_link = f"https://t.me/{bot_username}?start=ref_{uid}"
    price = format_price_uzs()

    from shared.keyboards import payment_choice_keyboard
    from shared.referral import referral_balance_block

    await callback.message.edit_text(
        f"💳 <b>Sotib olingan yuklashlar:</b> {status} ta\n"
        f"ℹ️ Ovoz va matn to'ldirish — <b>bepul</b>\n"
        f"💰 1 ta yuklash narxi: <b>{price} so'm</b>\n"
        f"Karta: <code>{settings.payment_card_number}</code>\n"
        f"Egasi: {settings.payment_card_owner}\n\n"
        f"{referral_balance_block(ref_link, progress)}",
        reply_markup=payment_choice_keyboard(uid, document_type=document_type),
    )


@router.callback_query(F.data == "pay_show_balance")
async def pay_show_balance(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if not callback.message or not callback.from_user:
        await callback.answer()
        return
    from features.bot.handlers.start import show_credits_for_uid

    await callback.answer()
    await show_credits_for_uid(callback.message, callback.from_user.id)


@router.message(PaymentStates.waiting_screenshot, F.text.func(is_menu_button))
async def payment_escape_to_menu(message: Message, state: FSMContext) -> None:
    """Chek kutishda menyu tugmalari ishlashi uchun."""
    await state.clear()
    text = message.text or ""
    if is_credits_button(text):
        from features.bot.handlers.start import show_credits_for_uid

        await show_credits_for_uid(message, message.from_user.id if message.from_user else 0)
        return
    if text in (BTN_SAMPLES,):
        await show_samples(message)
        return
    from features.bot.handlers.start import cmd_help, cv_intro, menu_back

    if text == BTN_CV:
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
    else:
        await message.answer("Bosh menyu:", reply_markup=user_menu(message.from_user.id if message.from_user else None))


@router.message(PaymentStates.waiting_screenshot, ~F.photo)
async def payment_screenshot_not_photo(message: Message) -> None:
    await message.answer(
        "❌ <b>Iltimos, faqat to'lov cheki rasmini (skrinshot) yuboring.</b>\n\n"
        "Bekor qilish uchun «❌ Bekor qilish» tugmasini bosing yoki 💳 Pul balansi menyusidan chiqing.",
    )


@router.message(PaymentStates.waiting_screenshot, F.photo)
async def process_payment_screenshot(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id if message.from_user else 0
    if uid and users_repo.is_blocked(uid):
        await message.answer("⛔ Siz bloklangansiz.")
        await state.clear()
        return

    data = await state.get_data()
    document_type = data.get("payment_document_type", "cv")
    label = data.get("payment_label", "CV Resume")
    await state.clear()

    # Get primary user name
    name = message.from_user.first_name or "Bot User"
    
    # Save the screenshot
    photo = message.photo[-1]
    file_info = await message.bot.get_file(photo.file_id)
    
    from config.settings import RECEIPTS_DIR
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # We must insert payment row first to obtain payment request ID
    payment = await db_run(payments_repo.create_payment, uid, payer_name=name, document_type=document_type)
    if not payment:
        await message.answer("❌ To'lov so'rovini saqlashda xatolik yuz berdi. Qayta urinib ko'ring.")
        return
        
    pid = int(payment["id"])
    path = RECEIPTS_DIR / f"{uid}_{pid}_{uuid.uuid4().hex[:8]}.jpg"
    
    try:
        await message.bot.download_file(file_info.file_path, str(path))
    except Exception as e:
        logger.exception("Failed to download payment receipt from bot: %s", e)
        await message.answer("❌ Rasmni yuklab olishda muammo yuz berdi. Iltimos, qaytadan yuborib ko'ring.")
        return

    # Update payment with screenshot path
    await db_run(payments_repo.update_receipt, pid, str(path))
    
    # Fetch updated payment data
    updated_payment = await db_run(payments_repo.get_payment, pid) or payment
    
    # Finalize (notifies admins, schedules auto-approve if enabled)
    await _finalize_payment_submission(updated_payment, uid, document_type, message.bot)

    await message.answer(
        f"✅ <b>Chek qabul qilindi!</b>\n\n"
        f"Admin to'lovingizni tekshirmoqda (odatda 1-2 daqiqa).\n"
        f"Tasdiqlanishi bilan sizga xabar yuboriladi va yuklash balansingiz ko'payadi.",
        reply_markup=user_menu(uid),
    )


@router.callback_query(F.data == "postpay_cover")
async def postpay_cover(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.message or not callback.from_user:
        await callback.answer("Xabar topilmadi", show_alert=True)
        return
    from features.bot.handlers.cover_letter import cmd_cover

    await cmd_cover(callback.message, state, actor_uid=callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "postpay_translate")
async def postpay_translate(callback: CallbackQuery) -> None:
    if not callback.message or not callback.from_user:
        await callback.answer("Xabar topilmadi", show_alert=True)
        return
    from features.bot.handlers.translate import cmd_translate

    await cmd_translate(callback.message, actor_uid=callback.from_user.id)
    await callback.answer()
