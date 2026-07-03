"""Aiogram 3 — AI Document Translation Router."""
from __future__ import annotations

import copy
import logging
import re
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from database.repositories import users as users_repo
from features.ai.gemini_client import is_ai_garbage, is_meaningfully_changed, translate_strings_batch
from features.obyektivka.malumotnoma_data import build_malumotnoma_data, normalize_obyektivka_raw
from features.obyektivka.none_values import field_or_none, is_none_token, none_for_lang
from features.obyektivka.translate_phrases import format_birth_year_place, translate_awards_phrase
from features.cv import service as cv_service
from features.obyektivka import service as oby_service
from shared.ai_errors import AiQuotaError, translate_error_to_user_message
from shared.async_db import run as db_run
from shared.export_delivery import send_bytes_to_telegram
from shared.name_patronymic import translate_patronymic_suffixes

logger = logging.getLogger(__name__)
router = Router()

TARGET_LABELS = {
    "en": "Ingliz",
    "ru": "Rus",
}


class TranslationError(Exception):
    """Document payload could not be translated."""


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


def _parse_action(action: str) -> tuple[str, str]:
    parts = (action or "").split("_")
    if len(parts) < 3:
        raise TranslationError("invalid_action")
    doc_raw, target = parts[1], parts[2]
    if doc_raw not in ("cv", "oby") or target not in TARGET_LABELS:
        raise TranslationError("invalid_action")
    doc_type = "cv" if doc_raw == "cv" else "obyektivka"
    return doc_type, target


def _direction_for(target: str) -> str:
    mapping = {
        "en": "uz_en",
        "ru": "uz_ru",
    }
    direction = mapping.get(target)
    if not direction:
        raise TranslationError("unsupported_direction")
    return direction


def _template_lang_code(target: str) -> str:
    if target == "en":
        return "en"
    if target == "ru":
        return "ru"
    raise TranslationError("unsupported_direction")


_LOCAL_PHRASES: dict[str, dict[str, str]] = {
    "uz_en": {
        "otasi": "Father",
        "onasi": "Mother",
        "opasi": "Elder sister",
        "singlisi": "Younger sister",
        "akasi": "Elder brother",
        "ukasi": "Younger brother",
        "turmush ortog'i": "Spouse",
        "xotini": "Wife",
        "eri": "Husband",
        "qaynotasi": "Father-in-law",
        "qaynonasi": "Mother-in-law",
        "o'g'li": "Son",
        "qizi": "Daughter",
        "ўзбек": "Uzbek",
        "o'zbek": "Uzbek",
        "ozbek": "Uzbek",
        "отаси": "Father",
        "онаси": "Mother",
        "balandroq": "Higher",
        "oliy": "Higher",
        "o'rta maxsus": "Secondary special",
        "o'rta": "Secondary",
        "tugallanmagan oliy": "Incomplete higher education",
        "rus tili": "Russian",
        "ingliz tili": "English",
        "turk tili": "Turkish",
        "nemis tili": "German",
        "fransuz tili": "French",
        "o'zbek tili": "Uzbek",
        "yuqori": "Higher",
        "oliy": "Higher",
        "o'rta maxsus": "Secondary special",
        "o'rta": "Secondary",
        "tugallanmagan oliy": "Incomplete higher education",
        "o'qituvchi": "Teacher",
        "ўқитувчи": "Teacher",
        "ўқитувчилар": "Teachers",
        "учитель": "Teacher",
        "учителя": "Teacher",
        "учители": "Teachers",
        "учителей": "Teachers",
        "toshkent shahri": "Tashkent city",
        "toshkent sh.": "Tashkent city",
        "dasturiy injiniring": "Software engineering",
        "ma'muriy injiniring": "Administrative engineering",
        "ma'muriy muhandislik": "Administrative engineering",
        "rus": "Russian",
        "tojik": "Tajik",
        "qozoq": "Kazakh",
    },
    "uz_ru": {
        "otasi": "Отец",
        "onasi": "Мать",
        "opasi": "Старшая сестра",
        "singlisi": "Младшая сестра",
        "akasi": "Старший брат",
        "ukasi": "Младший брат",
        "turmush ortog'i": "Супруг(а)",
        "xotini": "Жена",
        "eri": "Муж",
        "qaynotasi": "Свекор",
        "qaynonasi": "Свекровь",
        "o'g'li": "Сын",
        "qizi": "Дочь",
        "ўзбек": "Узбек",
        "o'zbek": "Узбек",
        "ozbek": "Узбек",
        "отаси": "Отец",
        "онаси": "Мать",
        "balandroq": "Высшее",
        "oliy": "Высшее",
        "o'rta maxsus": "Среднее специальное",
        "o'rta": "Среднее",
        "tugallanmagan oliy": "Незаконченное высшее",
        "rus tili": "Русский",
        "ingliz tili": "Английский",
        "turk tili": "Турецкий",
        "nemis tili": "Немецкий",
        "fransuz tili": "Французский",
        "o'zbek tili": "Узбекский",
        "yuqori": "Высшее",
        "oliy": "Высшее",
        "o'rta maxsus": "Среднее специальное",
        "o'rta": "Среднее",
        "tugallanmagan oliy": "Незаконченное высшее",
        "o'qituvchi": "Учитель",
        "ўқитувчи": "Учитель",
        "toshkent shahri": "г. Ташкент",
        "toshkent sh.": "г. Ташкент",
        "dasturiy injiniring": "Программная инженерия",
        "ma'muriy injiniring": "Административная инженерия",
        "ma'muriy muhandislik": "Административная инженерия",
        "rus": "Русский",
        "tojik": "Таджик",
        "qozoq": "Казах",
    },
}


def _local_translate_phrase(text: str, direction: str) -> str | None:
    key = (text or "").strip().lower().replace("ʻ", "'").replace("'", "'")
    mapping = _LOCAL_PHRASES.get(direction) or {}
    if key in mapping:
        return mapping[key]
    parts = [part.strip() for part in re.split(r"[,;]", text or "") if part.strip()]
    if len(parts) > 1:
        translated = []
        for part in parts:
            part_key = part.lower().replace("ʻ", "'").replace("'", "'")
            translated.append(mapping.get(part_key, part))
        if any(translated[i] != parts[i] for i in range(len(parts))):
            return ", ".join(translated)
    return None


def _has_cyrillic(text: str) -> bool:
    return bool(re.search(r"[\u0400-\u04ff]", text or ""))


def _restore_person_names(source: dict[str, Any], target: dict[str, Any], direction: str) -> None:
    for key in ("fullname", "name"):
        if source.get(key):
            target[key] = translate_patronymic_suffixes(str(source[key]), direction)
    for rel_key in ("relatives", "rels"):
        src_list = source.get(rel_key)
        tgt_list = target.get(rel_key)
        if not isinstance(src_list, list) or not isinstance(tgt_list, list):
            continue
        for idx, src_rel in enumerate(src_list):
            if idx >= len(tgt_list) or not isinstance(src_rel, dict) or not isinstance(tgt_list[idx], dict):
                continue
            for name_key in ("fullname", "name"):
                if src_rel.get(name_key):
                    tgt_list[idx][name_key] = translate_patronymic_suffixes(
                        str(src_rel[name_key]), direction
                    )


def _sanitize_translated_value(original: str, translated: str, direction: str) -> str:
    if is_ai_garbage(translated):
        if is_none_token(original):
            return none_for_lang("en" if direction.endswith("_en") else "ru")
        local = _local_translate_phrase(original, direction)
        if local is not None:
            return local
        return original
    if direction == "uz_en" and _has_cyrillic(translated) and not _has_cyrillic(original):
        local = _local_translate_phrase(original, direction)
        if local is not None:
            return local
        local_from_tr = _local_translate_phrase(translated, direction)
        if local_from_tr is not None:
            return local_from_tr
        return original
    return translated


def _is_relationship_degree_key(path: list, key: str) -> bool:
    """Qarindosh qatori slotiga tushishi uchun degree/type o'zgartirilmasin."""
    if key not in ("type", "degree"):
        return False
    if len(path) < 2:
        return False
    return path[0] in ("relatives", "rels") and isinstance(path[1], int)


def _is_person_name_key(path: list, key: str) -> bool:
    """Ism-familiyalar tarjima qilinmasin (Erali → Early xatosi)."""
    return key in ("fullname", "name")


def _try_local_special(text: str, path: list, key: str, direction: str) -> str | None:
    low_key = (key or "").lower()
    if low_key in ("awards", "award", "departmental_awards", "idor_awards", "idor"):
        return translate_awards_phrase(text, direction)
    if path and path[0] in ("relatives", "rels"):
        if low_key in ("birth_year_place", "birth"):
            return format_birth_year_place(text, direction)
        if low_key in ("work_place", "job"):
            return _local_translate_phrase(text, direction)
    return None


def _finalize_obyektivka_translation(payload: dict[str, Any], target: str) -> None:
    """Tarjimadan keyin: garbage tozalash, ish yili va mehnat qatorlarini qayta formatlash."""
    lang = _template_lang_code(target)
    payload["lang"] = lang

    scalar_keys = (
        "nation",
        "party",
        "education",
        "edu",
        "specialty",
        "spec",
        "degree",
        "deg",
        "scientific_title",
        "ttl",
        "languages",
        "langs",
        "military_rank",
        "mil",
        "awards",
        "award",
        "departmental_awards",
        "idor_awards",
        "idor",
        "deputy",
        "dep",
        "birthplace",
        "place",
        "graduated",
        "grad",
        "current_job",
    )
    for key in scalar_keys:
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            direction = _direction_for(target)
            local = _try_local_special(val, [], key, direction)
            if local is None:
                local = _local_translate_phrase(val, direction)
            if local is not None:
                payload[key] = local
            else:
                payload[key] = field_or_none(val, lang)

    for rel_list_key in ("relatives", "rels"):
        rels = payload.get(rel_list_key)
        if not isinstance(rels, list):
            continue
        direction = _direction_for(target)
        for idx, rel in enumerate(rels):
            if not isinstance(rel, dict):
                continue
            for rk, rv in list(rel.items()):
                if not isinstance(rv, str) or not rv.strip():
                    continue
                local = _try_local_special(rv, [rel_list_key, idx], rk, direction)
                if local is not None:
                    rel[rk] = local
                elif rk not in ("fullname", "name", "degree", "type"):
                    rel[rk] = field_or_none(rv, lang)

    normalized = normalize_obyektivka_raw(payload)
    mdata = build_malumotnoma_data({**normalized, "lang": lang})
    payload["current_job"] = mdata["current_job"]
    payload["current_job_year"] = mdata["current_job_year"]


def _collect_translatable_strings(payload: dict[str, Any]) -> list[tuple[list, str]]:
    exclude_keys = {
        "phone",
        "email",
        "img",
        "photo_data",
        "photo",
        "accent_color",
        "template",
        "lang",
        "id",
        "user_id",
        "status",
        "created_at",
        "updated_at",
        "gender",
        "birth_date",
        "birthdate",
        "f",
        "t",
        "from",
        "to",
        "date",
        "year",
        "from_year",
        "to_year",
    }

    def collect(data: Any, path: list) -> list[tuple[list, str]]:
        res: list[tuple[list, str]] = []
        if isinstance(data, dict):
            for key, value in data.items():
                if key in exclude_keys:
                    continue
                if _is_relationship_degree_key(path, key):
                    continue
                if _is_person_name_key(path, key):
                    continue
                res.extend(collect(value, path + [key]))
        elif isinstance(data, list):
            for index, item in enumerate(data):
                res.extend(collect(item, path + [index]))
        elif isinstance(data, str):
            val = data.strip()
            if not val:
                return res
            if val.startswith("data:") or len(val) > 200:
                if "," in val or (len(val) > 80 and " " not in val):
                    return res
            if "@" in val and " " not in val:
                return res
            if val.startswith("http://") or val.startswith("https://"):
                return res
            if val.startswith("#") and len(val) in (4, 7) and " " not in val:
                return res
            cleaned_num = (
                val.replace("+", "")
                .replace("-", "")
                .replace(" ", "")
                .replace("(", "")
                .replace(")", "")
            )
            if cleaned_num.isdigit():
                return res
            res.append((path, data))
        return res

    return collect(payload, [])


def _set_by_path(data: Any, path: list, value: Any) -> None:
    curr = data
    for key in path[:-1]:
        curr = curr[key]
    curr[path[-1]] = value


@router.message(Command("translate"))
async def cmd_translate(message: Message, *, actor_uid: int | None = None) -> None:
    uid = actor_uid or (message.from_user.id if message.from_user else 0)
    if not uid:
        return

    cv_data = await db_run(cv_service.get_saved_data, uid)
    oby_data = await db_run(oby_service.get_saved_data, uid) or await db_run(oby_service.get_pending, uid)

    has_cv = cv_data and cv_data.get("name") and len(str(cv_data.get("name")).strip()) > 0
    has_oby = (
        oby_data
        and (oby_data.get("fullname") or oby_data.get("name"))
        and len(str(oby_data.get("fullname") or oby_data.get("name")).strip()) > 0
    )

    if not has_cv and not has_oby:
        from shared.keyboards import webapp_url

        cv_url = webapp_url(uid, "cv.html")
        oby_url = webapp_url(uid, "obyektivka.html")

        inline_buttons = []
        if cv_url:
            inline_buttons.append(
                [
                    InlineKeyboardButton(
                        text="🚀 CV Resume to'ldirish",
                        web_app=WebAppInfo(url=f"{cv_url}&voice=1&autoload=1"),
                    )
                ]
            )
        if oby_url:
            inline_buttons.append(
                [
                    InlineKeyboardButton(
                        text="🚀 Obyektivka to'ldirish",
                        web_app=WebAppInfo(url=f"{oby_url}&voice=1&autoload=1"),
                    )
                ]
            )

        await message.answer(
            "❌ <b>Sizda hali tayyorlangan hujjatlar mavjud emas!</b>\n\n"
            "Matnni tarjima qilishdan oldin avval rezyume yoki obyektivka to'ldirib, uni yaratishingiz kerak.\n"
            "Iltimos, quyidagi tugmalar orqali ularni to'ldiring:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_buttons) if inline_buttons else user_menu(uid),
            parse_mode="HTML",
        )
        return

    await message.answer(
        "🌐 <b>Hujjatni boshqa tilga tarjima qilish (AI)</b>\n\n"
        "O'zbek tilidagi hujjatni ingliz yoki rus tiliga tarjima qiling.\n"
        "Hujjat turini va maqsadli tilni tanlang:\n"
        "<i>(Tarjima qilish 1 ta yuklash balansini sarflaydi)</i>",
        reply_markup=get_translate_kb(),
        parse_mode="HTML",
    )


async def translate_payload(
    payload: dict[str, Any],
    target: str,
) -> dict[str, Any]:
    translated_payload = copy.deepcopy(payload)

    results = _collect_translatable_strings(payload)
    if not results:
        translated_payload["lang"] = _template_lang_code(target)
        return translated_payload

    texts_to_translate = [value for _, value in results]
    direction = _direction_for(target)

    pending_texts: list[str] = []
    pending_indexes: list[int] = []
    translated_texts = list(texts_to_translate)

    for index, text in enumerate(texts_to_translate):
        path, _ = results[index]
        key = path[-1] if path else ""
        special = _try_local_special(text, path, str(key), direction)
        if special is not None:
            translated_texts[index] = special
            continue
        local = _local_translate_phrase(text, direction)
        if local is not None:
            translated_texts[index] = local
        else:
            pending_texts.append(text)
            pending_indexes.append(index)

    try:
        if pending_texts:
            ai_texts = await translate_strings_batch(pending_texts, direction)
            for idx, translated in zip(pending_indexes, ai_texts):
                translated_texts[idx] = _sanitize_translated_value(
                    texts_to_translate[idx], translated, direction
                )
    except RuntimeError as exc:
        if str(exc) == "translation_unavailable":
            raise TranslationError("translation_unavailable") from exc
        raise

    if len(translated_texts) != len(texts_to_translate):
        raise TranslationError("size_mismatch")

    changed = sum(
        1
        for original, translated in zip(texts_to_translate, translated_texts)
        if is_meaningfully_changed(original, translated)
    )
    if changed == 0:
        raise TranslationError("no_changes")

    for (path, _), translated_value in zip(results, translated_texts):
        _set_by_path(translated_payload, path, translated_value)

    _restore_person_names(payload, translated_payload, direction)
    if payload.get("name") and "name" in translated_payload:
        translated_payload["name"] = translate_patronymic_suffixes(str(payload["name"]), direction)
    translated_payload["lang"] = _template_lang_code(target)
    if "fullname" in payload or "relatives" in payload or "rels" in payload:
        _finalize_obyektivka_translation(translated_payload, target)
    return translated_payload


@router.callback_query(F.data.startswith("tr_"))
async def process_translation(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    action = callback.data or ""
    msg = callback.message
    if not msg:
        await callback.answer("Xabar topilmadi", show_alert=True)
        return

    try:
        doc_type, target = _parse_action(action)
    except TranslationError:
        await callback.answer("Noto'g'ri tanlov", show_alert=True)
        return

    lang_label = TARGET_LABELS[target]

    credits = await db_run(users_repo.get_credits, uid)
    if credits < 1:
        await callback.answer("Yuklashlar yetarli emas. Balansingizni to'ldiring.", show_alert=True)
        await msg.answer(
            "💳 <b>Balansingizda yuklashlar yetarli emas.</b>\n\n"
            "Hujjat tarjimasi 1 ta yuklash balansini sarflaydi.",
            reply_markup=insufficient_balance_keyboard(uid),
        )
        return

    if doc_type == "cv":
        data = await db_run(cv_service.get_saved_data, uid)
        label = "CV Resume"
        is_ready = data and data.get("name") and len(str(data.get("name")).strip()) > 0
    else:
        data = await db_run(oby_service.get_saved_data, uid) or await db_run(oby_service.get_pending, uid)
        label = "Obyektivka"
        is_ready = (
            data
            and (data.get("fullname") or data.get("name"))
            and len(str(data.get("fullname") or data.get("name")).strip()) > 0
        )

    if not is_ready:
        from shared.keyboards import webapp_url

        page = "cv.html" if doc_type == "cv" else "obyektivka.html"
        url = webapp_url(uid, page)
        inline_kb = None
        if url:
            inline_kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=f"🚀 {label} to'ldirish",
                            web_app=WebAppInfo(url=f"{url}&voice=1&autoload=1"),
                        )
                    ]
                ]
            )
        await msg.edit_text(
            f"❌ <b>Sizda hali tayyorlangan {label} hujjati mavjud emas!</b>\n\n"
            f"Tarjima qilishdan oldin avval {label} formasini to'ldirib, uni yaratishingiz kerak.",
            reply_markup=inline_kb,
            parse_mode="HTML",
        )
        await callback.answer()
        return

    await callback.answer()
    await msg.edit_text(f"⏳ <b>AI {label} ma'lumotlarini o'zbekdan {lang_label} tiliga tarjima qilmoqda...</b>")

    try:
        translated = await translate_payload(data, target)
        await msg.edit_text(f"⏳ <b>Yangi {label} fayli render qilinmoqda...</b>")

        bot = msg.bot
        if doc_type == "cv":
            pdf_bytes, filename = await cv_service.export_pdf(uid, translated, bot)
            sent = await send_bytes_to_telegram(
                bot,
                uid,
                pdf_bytes,
                filename,
                caption=(
                    f"✅ <b>CV {lang_label} tilida tayyorlandi!</b>\n"
                    f"<i>(Balansingizdan 1 ta yuklash sarflandi)</i>"
                ),
            )
        else:
            docx_bytes, filename = await oby_service.export_docx(uid, translated, bot)
            sent = await send_bytes_to_telegram(
                bot,
                uid,
                docx_bytes,
                filename,
                caption=(
                    f"✅ <b>Obyektivka {lang_label} tilida tayyorlandi!</b>\n"
                    f"<i>(Balansingizdan 1 ta yuklash sarflandi)</i>"
                ),
            )

        if sent:
            await msg.delete()
        else:
            await msg.edit_text("❌ Faylni Telegramga yuborib bo'lmadi. Qayta urinib ko'ring.")
    except PermissionError:
        await msg.edit_text(
            "💳 <b>Hisobingizda yuklashlar qolmagan.</b> Avval balansingizni to'ldiring.",
            reply_markup=insufficient_balance_keyboard(callback.from_user.id),
        )
    except AiQuotaError as exc:
        await msg.edit_text(translate_error_to_user_message(exc))
    except TranslationError as exc:
        reason = str(exc)
        if reason == "translation_unavailable":
            text = "❌ Tarjima xizmati vaqtincha ishlamayapti. 1-2 daqiqadan so'ng qayta urinib ko'ring."
        elif reason == "no_changes":
            text = (
                "❌ Hujjat matnlari tanlangan tilga o'zgarmadi.\n\n"
                "Ehtimol hujjat allaqachon shu tilda yoki tarjima natijasi original bilan bir xil chiqdi."
            )
        else:
            text = "❌ Tanlangan til uchun tarjima qilib bo'lmadi. Boshqa tilni sinab ko'ring."
        await msg.edit_text(text)
    except Exception as e:
        logger.exception("Document translation failed: %s", e)
        await msg.edit_text("❌ Tarjima qilishda kutilmagan xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.")
