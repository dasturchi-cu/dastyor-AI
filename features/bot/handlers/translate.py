"""Aiogram 3 — AI Document Translation Router."""
from __future__ import annotations

import json
import logging
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

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

    # Check if they have at least one document actually filled
    cv_data = await db_run(cv_service.get_saved_data, uid)
    oby_data = await db_run(oby_service.get_saved_data, uid) or await db_run(oby_service.get_pending, uid)

    has_cv = cv_data and cv_data.get("name") and len(str(cv_data.get("name")).strip()) > 0
    has_oby = oby_data and (oby_data.get("fullname") or oby_data.get("name")) and len(str(oby_data.get("fullname") or oby_data.get("name")).strip()) > 0

    if not has_cv and not has_oby:
        from shared.keyboards import webapp_url
        cv_url = webapp_url(uid, "cv.html")
        oby_url = webapp_url(uid, "obyektivka.html")
        
        inline_buttons = []
        if cv_url:
            inline_buttons.append([
                InlineKeyboardButton(text="🚀 CV Resume to'ldirish", web_app=WebAppInfo(url=f"{cv_url}&voice=1&autoload=1"))
            ])
        if oby_url:
            inline_buttons.append([
                InlineKeyboardButton(text="🚀 Obyektivka to'ldirish", web_app=WebAppInfo(url=f"{oby_url}&voice=1&autoload=1"))
            ])
            
        await message.answer(
            "❌ <b>Sizda hali tayyorlangan hujjatlar mavjud emas!</b>\n\n"
            "Matnni tarjima qilishdan oldin avval rezyume yoki obyektivka to'ldirib, uni yaratishingiz kerak.\n"
            "Iltimos, quyidagi tugmalar orqali ularni to'ldiring:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_buttons) if inline_buttons else user_menu(uid),
            parse_mode="HTML"
        )
        return

    await message.answer(
        "🌐 <b>Hujjatni boshqa tilga tarjima qilish (AI)</b>\n\n"
        "Tarjima qilinadigan hujjat turi va maqsadli tilni tanlang:\n"
        "<i>(Tarjima qilish 1 ta yuklash balansini sarflaydi)</i>",
        reply_markup=get_translate_kb(),
        parse_mode="HTML"
    )


async def translate_payload(payload: dict[str, Any], target_language: str) -> dict[str, Any]:
    import copy
    import json
    import re
    from features.ai.gemini_client import generate_text_with_fallback

    # 1. Walk payload to collect all translatable strings
    EXCLUDE_KEYS = {
        "phone", "email", "img", "photo_data", "photo", "accent_color",
        "template", "lang", "id", "user_id", "status", "created_at", "updated_at",
        "gender", "birth_date", "birthdate", "f", "t", "from", "to", "date", "year"
    }

    def collect(data: Any, path: list) -> list[tuple[list, str]]:
        res = []
        if isinstance(data, dict):
            for k, v in data.items():
                if k in EXCLUDE_KEYS:
                    continue
                res.extend(collect(v, path + [k]))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                res.extend(collect(item, path + [i]))
        elif isinstance(data, str):
            val = data.strip()
            if not val:
                return res
            # Skip base64 images
            if val.startswith("data:") or len(val) > 200:
                if "," in val or (len(val) > 80 and " " not in val):
                    return res
            # Skip email
            if "@" in val and " " not in val:
                return res
            # Skip URL
            if val.startswith("http://") or val.startswith("https://"):
                return res
            # Skip hex color
            if val.startswith("#") and len(val) in (4, 7) and " " not in val:
                return res
            # Skip pure numbers
            cleaned_num = val.replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
            if cleaned_num.isdigit():
                return res
            
            res.append((path, data))
        return res

    results = collect(payload, [])
    if not results:
        return payload

    texts_to_translate = [val for path, val in results]

    # 2. Translate strings as a flat JSON array
    json_to_send = json.dumps(texts_to_translate, ensure_ascii=False)
    prompt = f"""Siz professional tarjimonsiz. Quyidagi JSON ro'yxati (array) ichidagi matnlarni o'zbek tilidan {target_language} tiliga professional darajada tarjima qiling.
Qoidalar:
- Faqatgina matnlar qiymatini tarjima qiling, tartibini va ro'yxat uzunligini o'zgartirmang.
- Javob faqat va faqat tarjima qilingan matnlardan iborat bo'lgan to'g'ri JSON ro'yxati (array) bo'lishi shart.
- Hech qanday qo'shimcha tushuntirish, markdown bezaklari (```json kabi) qo'shmang. Faqat toza JSON javob bering.

Matnlar soni: {len(texts_to_translate)}

JSON:
{json_to_send}"""

    try:
        raw_text = await generate_text_with_fallback(prompt, timeout=60)
        if not raw_text or not raw_text.strip():
            logger.error("AI returned empty translation")
            return payload

        cleaned = raw_text.strip()
        # Remove markdown wrapping
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n", "", cleaned)
            cleaned = re.sub(r"\n```$", "", cleaned)
        cleaned = cleaned.strip()

        # Regex search for first '[' to last ']'
        match = re.search(r"(\[.*\])", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1)

        translated_texts = json.loads(cleaned)
        if not isinstance(translated_texts, list) or len(translated_texts) != len(texts_to_translate):
            logger.error(
                "Translation array size mismatch. Expected %d, got %d. Raw: %s",
                len(texts_to_translate),
                len(translated_texts) if isinstance(translated_texts, list) else -1,
                raw_text
            )
            return payload

        # 3. Map translated strings back into a deep copy of payload
        translated_payload = copy.deepcopy(payload)

        def set_by_path(d: Any, p: list, value: Any):
            curr = d
            for key in p[:-1]:
                curr = curr[key]
            curr[p[-1]] = value

        for (p, _), trans_val in zip(results, translated_texts):
            set_by_path(translated_payload, p, trans_val)

        return translated_payload

    except Exception as e:
        logger.exception("Failed in robust translate_payload: %s", e)
        return payload


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

    # Load data and check if actually ready
    if doc_type == "cv":
        data = await db_run(cv_service.get_saved_data, uid)
        label = "CV Resume"
        is_ready = data and data.get("name") and len(str(data.get("name")).strip()) > 0
    else:
        data = await db_run(oby_service.get_saved_data, uid) or await db_run(oby_service.get_pending, uid)
        label = "Obyektivka"
        is_ready = data and (data.get("fullname") or data.get("name")) and len(str(data.get("fullname") or data.get("name")).strip()) > 0

    if not is_ready:
        from shared.keyboards import webapp_url
        page = "cv.html" if doc_type == "cv" else "obyektivka.html"
        url = webapp_url(uid, page)
        inline_kb = None
        if url:
            inline_kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=f"🚀 {label} to'ldirish", web_app=WebAppInfo(url=f"{url}&voice=1&autoload=1"))
            ]])
        await callback.message.edit_text(
            f"❌ <b>Sizda hali tayyorlangan {label} hujjati mavjud emas!</b>\n\n"
            f"Tarjima qilishdan oldin avval {label} formasini to'ldirib, uni yaratishingiz kerak.",
            reply_markup=inline_kb,
            parse_mode="HTML"
        )
        await callback.answer()
        return

    await callback.message.edit_text(f"⏳ <b>AI {label} ma'lumotlarini {lang} tiliga tarjima qilmoqda...</b>")

    try:
        translated = await translate_payload(data, lang)
        
        # Set proper language code for templates
        if doc_type == "cv":
            translated["lang"] = "en" if "en" in action else "ru"
        else:
            # Obyektivka technically has no separate layout language template for English/Russian,
            # but we update the lang tag just in case
            translated["lang"] = "uz_lat"
        
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
