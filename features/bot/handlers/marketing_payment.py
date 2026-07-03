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
from shared.keyboards import BTN_SAMPLES, user_menu
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
    cv_path = PROJECT_ROOT / "assets" / "samples" / "cv_sample.png"
    if cv_path.is_file():
        await message.answer_photo(
            FSInputFile(cv_path),
            caption="📄 <b>CV (Resume) shablonimiz namunasi</b>\n\nZamonaviy va professional dizayn, ish beruvchilar diqqatini tortadigan struktura.",
        )
    else:
        logger.warning("CV sample file not found at %s", cv_path)

    # Send Obyektivka sample
    oby_path = PROJECT_ROOT / "assets" / "samples" / "obyektivka_sample.png"
    if oby_path.is_file():
        await message.answer_photo(
            FSInputFile(oby_path),
            caption="✍️ <b>Obyektivka (Ma'lumotnoma) shablonimiz namunasi</b>\n\nDavlat va xususiy tashkilotlar standarti asosida tayyorlanadigan rasmiy format.",
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
    kind_raw = callback.data.split("_")[-1]
    kind = "cv" if kind_raw in ("cv", "cover", "translate") else "obyektivka"
    if kind_raw == "cv":
        label = "CV Resume"
    elif kind_raw == "cover":
        label = "Muqova xati"
    elif kind_raw == "translate":
        label = "Hujjat tarjimasi"
    else:
        label = "Obyektivka"

    await state.set_state(PaymentStates.waiting_screenshot)
    await state.update_data(payment_kind=kind, payment_label=label)

    await callback.message.edit_text(
        f"💳 <b>{label} to'lovi (7,999 so'm)</b>\n\n"
        f"Karta: <code>{settings.payment_card_number}</code>\n"
        f"Egasi: <b>{settings.payment_card_owner}</b>\n\n"
        f"Iltimos, to'lovni amalga oshirgach, to'lov cheki rasm/skrinshotini shu yerga yuboring 👇",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="pay_cancel")]
            ]
        )
    )


@router.callback_query(F.data == "pay_cancel")
async def cancel_bot_payment(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    uid = callback.from_user.id
    status = await db_run(users_repo.get_credits, uid)
    ref_count = await db_run(users_repo.get_referral_count, uid)
    bot_username = settings.bot_username or "DastyorAiBot"
    ref_link = f"https://t.me/{bot_username}?start=ref_{uid}"
    
    from shared.keyboards import payment_choice_keyboard
    await callback.message.edit_text(
        f"💳 <b>Sotib olingan yuklashlar:</b> {status} ta\n"
        f"ℹ️ Ovoz va matn to'ldirish — <b>bepul</b>\n"
        f"💰 1 ta yuklash narxi: <b>7,999 so'm</b>\n"
        f"Karta: <code>{settings.payment_card_number}</code>\n"
        f"Egasi: {settings.payment_card_owner}\n\n"
        f"👥 <b>Siz taklif qilgan faol do'stlaringiz:</b> {ref_count} ta\n"
        f"🎁 <b>Bepul yuklash olish:</b> Do'stlaringizga taklif havolangizni ulashing. Har 3 ta do'stingiz botdan foydalanib o'zining birinchi bepul hujjatini yuklab olganida sizga +1 ta bepul yuklash sovg'a qilinadi!\n"
        f"Havolangiz:\n<code>{ref_link}</code>",
        reply_markup=payment_choice_keyboard(uid),
    )


@router.message(PaymentStates.waiting_screenshot, ~F.photo)
async def payment_screenshot_not_photo(message: Message) -> None:
    await message.answer(
        "❌ <b>Iltimos, faqat to'lov cheki rasmini (skrinshot) yuboring.</b>\n"
        "Agar to'lovni bekor qilmoqchi bo'lsangiz, /start buyrug'ini bosing."
    )


@router.message(PaymentStates.waiting_screenshot, F.photo)
async def process_payment_screenshot(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id if message.from_user else 0
    if uid and users_repo.is_blocked(uid):
        await message.answer("⛔ Siz bloklangansiz.")
        await state.clear()
        return

    data = await state.get_data()
    kind = data.get("payment_kind", "cv")
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
    payment = await db_run(payments_repo.create_payment, uid, payer_name=name, document_type=kind)
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
    await _finalize_payment_submission(updated_payment, uid, kind, message.bot)

    await message.answer(
        f"✅ <b>Chek qabul qilindi!</b>\n\n"
        f"Admin to'lovingizni tekshirmoqda (odatda 1-2 daqiqa).\n"
        f"Tasdiqlanishi bilan sizga xabar yuboriladi va yuklash balansingiz ko'payadi.",
        reply_markup=user_menu(uid),
    )
