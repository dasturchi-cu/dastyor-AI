"""Aiogram 3 — AI Document Translation Router."""
from __future__ import annotations

import json
import logging
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database.repositories import users as users_repo
from features.cv import service as cv_service
from features.obyektivka import service as oby_service
from features.ai.gemini_client import generate_text_with_fallback
from shared.async_db import run as db_run
from shared.keyboards import user_menu
from shared.export_delivery import send_bytes_to_telegram

logger = logging.getLogger(__name__)
router = Router()


def get_translate_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📄 CV 🇺🇸 Inglizchaga", callback_data="tr_cv_en"),
                InlineKeyboardButton(text="📄 CV 🇷🇺 Ruschaga", callback_data="tr_cv_ru"),
            ],
            [
                InlineKeyboardButton(text="✍️ Obyektivka 🇺🇸 Inglizchaga", callback_data="tr_oby_en"),
                InlineKeyboardButton(text="✍️ Obyektivka 🇷🇺 Ruschaga", callback_data="tr_oby_ru"),
            ],
        ]
    )


@router.message(Command("translate"))
async def cmd_translate(message: Message) -> None:
    uid = message.from_user.id if message.from_user else 0
    if not uid:
        return

    # Check if they have at least one document
    cv_data = await db_run(cv_service.get_saved_data, uid)
    oby_data = await db_run(oby_service.get_saved_data, uid) or await db_run(oby_service.get_pending, uid)

    if not cv_data and not oby_data:
        await message.answer(
            "❌ <b>Sizda hali saqlangan hujjatlar mavjud emas.</b>\n\n"
            "Avval rezyume yoki obyektivka yarating.",
            reply_markup=user_menu(uid),
        )
        return

    await message.answer(
        "🌐 <b>Hujjatni boshqa tilga tarjima qilish (AI)</b>\n\n"
        "Tarjima qilinadigan hujjat turi va maqsadli tilni tanlang:\n"
        "<i>(Tarjima qilish 1 ta yuklash balansini sarflaydi)</i>",
        reply_markup=get_translate_kb(),
    )


async def translate_payload(payload: dict[str, Any], target_language: str) -> dict[str, Any]:
    import re
    json_str = json.dumps(payload, ensure_ascii=False)
    prompt = f"""
Siz professional tarjimonsiz. Quyidagi JSON formatidagi ma'lumotlarning kalitlarini (keys) o'zgartirmasdan, ularning qiymatlarini (values) o'zbek tilidan {target_language} tiliga professional darajada tarjima qiling.

JSON:
{json_str}

Qoidalar:
- Kalitlarni (keys) aslo o'zgartirmang va tarjima qilmang, faqat ularga tegishli bo'lgan qiymatlarni (values) tarjima qiling.
- Faqat to'g'ri JSON formatida javob bering.
- Har qanday qo'shimcha tushuntirish yoki markdown kod bloklarini (masalan, ```json) qo'shmang.
- Agar qiymat bo'sh bo'lsa yoki ism/telefon kabi tarjima qilinmaydigan narsa bo'lsa, o'zgarishsiz qoldiring.
- OTM nomlari, kasblar va ish tajribalarini tarjimada to'g'ri ko'rsating.
"""
    raw_text = await generate_text_with_fallback(prompt, timeout=60)
    if not raw_text or not raw_text.strip():
        raise ValueError("AI returned an empty translation response")

    cleaned = raw_text.strip()
    # Remove markdown code block wrapping
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n", "", cleaned)
        cleaned = re.sub(r"\n```$", "", cleaned)
    cleaned = cleaned.strip()

    # Regex search for first '{' to last '}' to strip any conversational prefixes/suffixes
    match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("JSON decode error in translation: %s. Raw text: %s", e, raw_text)
        raise


@router.callback_query(F.data.startswith("tr_"))
async def process_translation(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    action = callback.data # tr_cv_en, tr_cv_ru, tr_oby_en, tr_oby_ru
    
    doc_type = "cv" if "cv" in action else "obyektivka"
    lang = "English" if "en" in action else "Russian"
    
    # Check credits first
    credits = await db_run(users_repo.get_credits, uid)
    if credits < 1:
        await callback.answer("Yuklashlar yetarli emas. Balansingizni to'ldiring.", show_alert=True)
        return

    # Load data
    if doc_type == "cv":
        data = await db_run(cv_service.get_saved_data, uid)
        label = "CV"
    else:
        data = await db_run(oby_service.get_saved_data, uid) or await db_run(oby_service.get_pending, uid)
        label = "Obyektivka"

    if not data:
        await callback.answer(f"Sizda hali saqlangan {label} ma'lumotlari yo'q.", show_alert=True)
        return

    await callback.message.edit_text(f"⏳ <b>AI {label} ma'lumotlarini {lang} tiliga tarjima qilmoqda...</b>")

    try:
        translated = await translate_payload(data, lang)
        
        await callback.message.edit_text(f"⏳ <b>Yangi {label} fayli render qilinmoqda...</b>")

        bot = callback.message.bot
        if doc_type == "cv":
            # Consumes 1 credit
            pdf_bytes, filename = await cv_service.export_pdf(uid, translated, bot)
            sent = await send_bytes_to_telegram(
                bot,
                uid,
                pdf_bytes,
                filename,
                caption=f"✅ <b>CV {lang} tilida tayyorlandi!</b>\n<i>(Balansingizdan 1 ta yuklash sarflandi)</i>",
            )
        else:
            # Consumes 1 credit
            docx_bytes, filename = await oby_service.export_docx(uid, translated, bot)
            sent = await send_bytes_to_telegram(
                bot,
                uid,
                docx_bytes,
                filename,
                caption=f"✅ <b>Obyektivka {lang} tilida tayyorlandi!</b>\n<i>(Balansingizdan 1 ta yuklash sarflandi)</i>",
            )
            
        if sent:
            await callback.message.delete()
        else:
            await callback.message.edit_text("❌ Faylni Telegramga yuborib bo'lmadi. Qayta urinib ko'ring.")
    except PermissionError:
        await callback.message.edit_text("💳 <b>Hisobingizda yuklashlar qolmagan.</b> Iltimos, balansingizni to'ldiring.")
    except Exception as e:
        logger.exception("Document translation failed: %s", e)
        await callback.message.edit_text("❌ Tarjima qilishda kutilmagan xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.")
