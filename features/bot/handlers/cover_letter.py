"""Aiogram 3 — AI Cover Letter Router."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database.repositories import users as users_repo
from database.repositories import cv_data as cv_repo
from features.bot.states import CvStates
from features.ai.gemini_client import generate_text_with_fallback
from shared.async_db import run as db_run
from shared.keyboards import insufficient_balance_keyboard, user_menu

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("cover"))
async def cmd_cover(message: Message, state: FSMContext, *, actor_uid: int | None = None) -> None:
    await state.clear()
    uid = actor_uid or (message.from_user.id if message.from_user else 0)
    if not uid:
        return

    # Check if user has a saved CV
    cv_data = await db_run(cv_repo.get, uid)
    if not cv_data or not cv_data.get("name"):
        await message.answer(
            "❌ <b>Sizda hali saqlangan CV mavjud emas.</b>\n\n"
            "Avval bosh menyudan 📄 CV bo'limiga kirib, formani to'ldiring.",
            reply_markup=user_menu(uid),
        )
        return

    # Check credits
    credits = await db_run(users_repo.get_credits, uid)
    if credits < 1:
        await message.answer(
            "💳 <b>Balansingizda yuklashlar yetarli emas.</b>\n\n"
            "Muqova xati (Cover Letter) yaratish 1 ta yuklash balansini sarflaydi.",
            reply_markup=insufficient_balance_keyboard(uid),
        )
        return

    await state.set_state(CvStates.waiting_cover_letter_vacancy)
    await message.answer(
        "📝 <b>AI Muqova xati (Cover Letter) yozish</b>\n\n"
        "Iltimos, ish beruvchining e'lonini (vakansiya matnini yoki tavsifini) yuboring. "
        "AI sizning CV ma'lumotlaringiz asosida ushbu vakansiyaga moslashtirilgan professional muqova xatini tayyorlaydi.",
        reply_markup=user_menu(uid),
    )


@router.message(CvStates.waiting_cover_letter_vacancy, F.text, ~F.text.startswith("/"))
async def process_vacancy_text(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id if message.from_user else 0
    if not uid or not message.text:
        return

    # Double check credits before processing
    credits = await db_run(users_repo.get_credits, uid)
    if credits < 1:
        await state.clear()
        await message.answer(
            "💳 <b>Hisobingizda yuklashlar qolmagan.</b> Avval balansingizni to'ldiring.",
            reply_markup=insufficient_balance_keyboard(uid),
        )
        return

    status = await message.answer("⏳ <b>AI Muqova xatini tayyorlamoqda...</b>\nIltimos, kutib turing.")

    try:
        cv_data = await db_run(cv_repo.get, uid)
        vacancy_text = message.text

        prompt = f"""
Siz professional HR mutaxassisisiz. Quyidagi nomzodning CV ma'lumotlari va vakansiya tavsifi asosida juda professional, jalb qiluvchi va lo'nda Cover Letter (Muqova xati) yozib bering.

Nomzod CV ma'lumotlari:
{cv_data}

Vakansiya tavsifi:
{vacancy_text}

Qoidalar:
- O'zbek tilida, imlo xatolarisiz va o'ta madaniyatli (sizlash ohangida) yozing.
- Nomzodning kuchli tomonlarini vakansiyaga moslab bering.
- Har qanday gaplarni to'qib chiqarmang, faqat nomzod CV'sida bor faktlarga tayaning.
- Faqat Muqova xati matnini qaytaring. Qo'shimcha sharhlar yoki kirish so'zlari yozmang.
"""
        cover_letter = await generate_text_with_fallback(prompt, timeout=60)
        
        if not cover_letter or len(cover_letter.strip()) < 10:
            await status.edit_text("❌ Muqova xatini yaratib bo'lmadi. Qayta urinib ko'ring.")
            return

        # Deduct credit
        await db_run(users_repo.consume_credit, uid)
        await state.clear()

        try:
            await status.delete()
        except Exception:
            pass
        await message.answer(
            "✅ <b>Muqova xati (Cover Letter) muvaffaqiyatli tayyorlandi!</b>\n"
            "<i>(Balansingizdan 1 ta yuklash sarflandi)</i>\n\n"
            f"<blockquote expandable>{cover_letter}</blockquote>",
            reply_markup=user_menu(uid),
        )
    except Exception as e:
        logger.exception("Cover letter generation failed: %s", e)
        try:
            await status.delete()
        except Exception:
            pass
        await message.answer(
            "❌ Muqova xati yaratishda xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.",
            reply_markup=user_menu(uid),
        )
