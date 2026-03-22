"""WebApp JSON APIs: auth, profile, messaging, transliteration, translate, spellcheck, objective."""
from __future__ import annotations

import html as html_lib
import io
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from telegram import InputFile

from backend.dependencies import get_ptb_application
from backend.schemas.webapp import (
    AuthRequest,
    NotifyRequest,
    ObjectiveRequest,
    SpellcheckRequest,
    SupportRequest,
    TranslateRequest,
    TranslitRequest,
)
from backend.services.spellcheck_cache import spellcheck_cache_get, spellcheck_cache_key, spellcheck_cache_set
from backend.services.user_resolve import resolve_telegram_uid
from backend.services.web_quota import web_quota_after, web_quota_before
from backend.settings import get_settings
from backend.web_constants import (
    BOT_USERNAME,
    NOTIFY_MAX_CHARS,
    SPELLCHECK_MAX_CHARS,
    TRANSLATE_MAX_CHARS,
    TRANSLIT_MAX_CHARS,
    WEBAPP_BASE,
    WEBAPP_VERSION,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["web-api"])


def _resolve_web_uid_optional(telegram_id: Optional[int], token: Optional[str]) -> Optional[int]:
    uid = resolve_telegram_uid(str(telegram_id) if telegram_id is not None else None, token)
    return int(uid) if uid else None


@router.post("/api/auth")
async def api_auth(req: AuthRequest):
    try:
        from bot.services.session_service import create_session
        from bot.services.user_service import track_user_activity

        token = create_session(
            telegram_id=req.telegram_id,
            first_name=req.first_name,
            username=req.username,
            photo_url=req.photo_url,
        )

        class _FakeUser:
            id = req.telegram_id
            first_name = req.first_name
            username = req.username

        track_user_activity(
            _FakeUser(), command="web_auth", chat_id=int(req.telegram_id)
        )
        return {"ok": True, "token": token, "telegram_id": req.telegram_id}
    except Exception as e:
        logger.error("/api/auth error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.get("/api/me")
async def api_me(
    token: Optional[str] = Query(None),
    telegram_id: Optional[str] = Query(None),
):
    uid = resolve_telegram_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")

    from bot.services.session_service import get_session_by_telegram_id
    from bot.services.settings_service import is_premium
    from bot.services.user_service import get_user_profile
    from bot.services.usage_tracker import get_tariff_snapshot

    profile = get_user_profile(uid) or {}
    session = get_session_by_telegram_id(uid) or {}
    tariff = get_tariff_snapshot(int(uid))

    return {
        "ok": True,
        "telegram_id": uid,
        "first_name": session.get("first_name", profile.get("first_name", "")),
        "username": session.get("username", profile.get("username", "")),
        "photo_url": session.get("photo_url", ""),
        "is_premium": is_premium(int(uid)),
        "files_processed": profile.get("files_processed", 0),
        "joined_at": profile.get("joined_at", ""),
        "last_active": profile.get("last_active", ""),
        **tariff,
    }


@router.post("/api/translit")
async def api_translit(req: TranslitRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Matn bo'sh bo'lishi mumkin emas")
    if len(req.text) > TRANSLIT_MAX_CHARS:
        raise HTTPException(status_code=400, detail="Matn 50 000 belgidan oshmasligi kerak")

    valid = {"krill_to_lotin", "lotin_to_krill"}
    if req.direction not in valid:
        raise HTTPException(status_code=400, detail=f"Noto'g'ri yo'nalish: {req.direction}")

    uid = _resolve_web_uid_optional(req.telegram_id, req.token)
    if uid:
        from bot.services.plan_limits import CAT_TRANSLIT

        web_quota_before(uid, CAT_TRANSLIT)

    try:
        from bot.services.transliterate_service import transliterate

        result = transliterate(req.text, req.direction)  # type: ignore[arg-type]
        if uid:
            from bot.services.plan_limits import CAT_TRANSLIT

            web_quota_after(uid, CAT_TRANSLIT, "Web translit")
        return {"ok": True, "result": result, "direction": req.direction}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("/api/translit error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.get("/api/bot-link")
async def api_bot_link(
    action: str = Query(..., description="cv | obyektivka | ocr | pdf | translit | translate"),
    telegram_id: Optional[str] = Query(None),
):
    page_map = {
        "cv": "cv.html",
        "obyektivka": "obyektivka.html",
        "ocr": "ocr.html",
        "pdf": "img2pdf.html",
        "translit": "translit.html",
        "translate": "translate.html",
        "premium": "premium.html",
    }
    page = page_map.get(action)
    if not page:
        raise HTTPException(status_code=400, detail=f"Noma'lum action: {action}")

    bot_link = f"https://t.me/{BOT_USERNAME}?start={action}"
    tid_param = f"?telegram_id={telegram_id}" if telegram_id else ""
    v_param = f"{'&' if tid_param else '?'}v={WEBAPP_VERSION}"
    webapp_url = f"{WEBAPP_BASE}/{page}{tid_param}{v_param}"
    return {"ok": True, "bot_link": bot_link, "webapp_url": webapp_url, "action": action}


@router.get("/api/stats")
async def api_stats(
    token: Optional[str] = Query(None),
    telegram_id: Optional[str] = Query(None),
):
    uid = resolve_telegram_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")

    from bot.services.settings_service import is_premium
    from bot.services.user_service import get_user_profile

    profile = get_user_profile(uid) or {}
    premium = is_premium(int(uid))

    return {
        "ok": True,
        "telegram_id": uid,
        "is_premium": premium,
        "files_processed": profile.get("files_processed", 0),
        "sessions": profile.get("sessions", 1),
        "last_service": profile.get("last_service", ""),
        "last_active": profile.get("last_active", ""),
        "joined_at": profile.get("joined_at", ""),
    }


@router.post("/api/notify")
async def api_notify(
    req: NotifyRequest,
    ptb=Depends(get_ptb_application),
):
    uid = resolve_telegram_uid(str(req.telegram_id), req.token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")

    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Xabar bo'sh")
    if len(req.message) > NOTIFY_MAX_CHARS:
        raise HTTPException(status_code=400, detail="Xabar 4000 belgi oshmasligi kerak")

    try:
        await ptb.bot.send_message(
            chat_id=int(uid),
            text=req.message,
            parse_mode="HTML",
        )
        return {"ok": True}
    except Exception as e:
        logger.warning("/api/notify failed for %s: %s", uid, e)
        raise HTTPException(status_code=502, detail=f"Telegram xatosi: {str(e)[:200]}")


@router.post("/api/support")
async def api_support(
    req: SupportRequest,
    ptb=Depends(get_ptb_application),
):
    uid = resolve_telegram_uid(str(req.telegram_id), req.token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")

    msg = (req.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Xabar bo'sh")
    if len(msg) > NOTIFY_MAX_CHARS:
        raise HTTPException(status_code=400, detail="Xabar 4000 belgidan oshmasligi kerak")

    admin_ids: list[int] = []
    raw_admin = (os.getenv("ADMIN_USER_ID") or "").strip()
    if raw_admin:
        admin_ids.extend(
            int(x.strip()) for x in raw_admin.split(",") if x.strip().lstrip("-").isdigit()
        )
    support_group = os.getenv("SUPPORT_GROUP_ID", "").strip()
    if support_group and support_group.lstrip("-").isdigit():
        admin_ids.append(int(support_group))

    if not admin_ids:
        admin_ids.append(-1003457224552)

    username = (req.username or "").strip()
    username_text = f"@{username}" if username else "yo'q"
    support_item = None
    try:
        from bot.services.support_service import create_support_request

        support_item = create_support_request(
            user_id=int(uid),
            username=username,
            message=msg,
            source="webapp",
        )
    except Exception as e:
        logger.warning("/api/support save failed: %s", e)

    ticket_line = f"🎫 Request ID: <b>#{support_item['id']}</b>\n" if support_item else ""
    text = (
        "📩 <b>WebApp support so'rovi</b>\n\n"
        f"{ticket_line}"
        f"🆔 User ID: <code>{uid}</code>\n"
        f"👤 Username: {username_text}\n\n"
        f"💬 Xabar:\n{msg}"
    )

    sent = 0
    for chat_id in dict.fromkeys(admin_ids):
        try:
            await ptb.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
            )
            sent += 1
        except Exception as e:
            logger.warning("/api/support forward failed to %s: %s", chat_id, e)

    if sent == 0:
        raise HTTPException(status_code=502, detail="Support xabarini yuborib bo'lmadi")

    return {"ok": True, "forwarded_to": sent}


@router.post("/api/translate")
async def api_translate(req: TranslateRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Matn bo'sh bo'lishi mumkin emas")
    if len(req.text) > TRANSLATE_MAX_CHARS:
        raise HTTPException(status_code=400, detail="Matn 5000 belgidan oshmasligi kerak")

    valid_dirs = {"uz_en", "en_uz", "ru_uz", "uz_ru", "ru_en", "en_ru"}
    if req.direction not in valid_dirs:
        raise HTTPException(status_code=400, detail=f"Noto'g'ri yo'nalish: {req.direction}")

    uid = _resolve_web_uid_optional(req.telegram_id, req.token)
    if uid:
        from bot.services.plan_limits import CAT_TRANSLATE

        web_quota_before(uid, CAT_TRANSLATE)

    try:
        from bot.services.ai_service import translate_text

        result = await translate_text(req.text, req.direction)
        if not result or result.startswith("Tarjimada xato") or result.startswith("AI model"):
            raise HTTPException(status_code=502, detail=result or "Tarjima bo'sh qaytdi")
        if uid:
            from bot.services.plan_limits import CAT_TRANSLATE

            web_quota_after(uid, CAT_TRANSLATE, "Web translate")
        return {"ok": True, "translated_text": result, "direction": req.direction}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Translate API error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Tarjima serveri xatosi: {str(e)[:200]}")


@router.post("/api/spellcheck")
async def api_spellcheck(req: SpellcheckRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Matn bo'sh bo'lishi mumkin emas")
    if len(req.text) > SPELLCHECK_MAX_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Matn {SPELLCHECK_MAX_CHARS} belgidan oshmasligi kerak",
        )

    uid = _resolve_web_uid_optional(req.telegram_id, req.token)
    if uid:
        from bot.services.plan_limits import CAT_SPELL

        web_quota_before(uid, CAT_SPELL)

    try:
        from bot.services.ai_service import check_spelling_text, count_words_text

        src = req.text.strip()
        wc = count_words_text(src)
        key = spellcheck_cache_key(src)
        hit = spellcheck_cache_get(key)
        if hit is not None:
            corrected, fixes = hit
            fc = int(fixes or 0)
            if uid:
                from bot.services.plan_limits import CAT_SPELL

                web_quota_after(uid, CAT_SPELL, "Web spell text")
            return {
                "ok": True,
                "corrected_text": corrected,
                "fixed": fc,
                "error_count": fc,
                "word_count": wc,
            }

        corrected, fixes = await check_spelling_text(src)
        if corrected is None:
            raise HTTPException(status_code=502, detail="Natija bo'sh qaytdi")

        spellcheck_cache_set(key, corrected, int(fixes or 0))
        fc = int(fixes or 0)
        if uid:
            from bot.services.plan_limits import CAT_SPELL

            web_quota_after(uid, CAT_SPELL, "Web spell text")
        return {
            "ok": True,
            "corrected_text": corrected,
            "fixed": fc,
            "error_count": fc,
            "word_count": wc,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Spellcheck API error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Imlo serveri xatosi: {str(e)[:200]}")


@router.post("/api/spellcheck_file")
async def api_spellcheck_file(
    file: UploadFile = File(...),
    token: Optional[str] = Form(None),
    telegram_id: Optional[str] = Form(None),
    notify_telegram: str = Form("false"),
    ptb=Depends(get_ptb_application),
):
    """
    Extract text from .txt / .docx / .pptx / .pdf → spell-check → JSON.
    Optional: send corrected UTF-8 .txt to the user's Telegram chat.
    """
    uid = resolve_telegram_uid(telegram_id, token)
    max_b = get_settings().max_upload_bytes
    raw = await file.read()
    do_notify = str(notify_telegram).lower() in ("1", "true", "yes", "on")
    if uid:
        do_notify = True
    uid_int = int(uid) if uid else None
    if uid_int:
        from bot.services.plan_limits import CAT_SPELL

        web_quota_before(uid_int, CAT_SPELL)
    logger.info(
        "POST /api/spellcheck_file name=%s bytes=%s notify=%s uid=%s",
        file.filename,
        len(raw),
        do_notify,
        uid or "-",
    )
    if not raw:
        raise HTTPException(status_code=400, detail="Bo'sh fayl")
    if len(raw) > max_b:
        raise HTTPException(status_code=413, detail="Fayl juda katta")

    try:
        from bot.services.document_text_extract import extract_plain_text_from_bytes

        text = extract_plain_text_from_bytes(file.filename or "upload.txt", raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if not (text or "").strip():
        raise HTTPException(status_code=422, detail="Fayldan matn ajratilmadi")

    src = text.strip()
    if len(src) > SPELLCHECK_MAX_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Matn {SPELLCHECK_MAX_CHARS} belgidan oshmasligi kerak",
        )

    from bot.services.ai_service import check_spelling_text, count_words_text

    wc = count_words_text(src)
    key = spellcheck_cache_key(src)
    hit = spellcheck_cache_get(key)
    if hit is not None:
        corrected, fixes = hit
    else:
        corrected, fixes = await check_spelling_text(src)
        if corrected is None:
            raise HTTPException(status_code=502, detail="Natija bo'sh qaytdi")
        spellcheck_cache_set(key, corrected, int(fixes or 0))

    fc = int(fixes or 0)
    out = {
        "ok": True,
        "corrected_text": corrected,
        "fixed": fc,
        "error_count": fc,
        "word_count": wc,
        "filename": file.filename or "document",
    }

    if uid_int:
        from bot.services.plan_limits import CAT_SPELL

        web_quota_after(uid_int, CAT_SPELL, "Web spell file")

    if do_notify and uid:
        try:
            from bot.services.user_service import get_chat_id
            from bot.services.supabase_db import db_insert_action_log

            chat_id = get_chat_id(int(uid)) or int(uid)
            summary = f"✅ Imlo tekshiruvi (WebApp)\nSo'zlar: {wc}\nTopilgan xatolar: {fc}"
            await ptb.bot.send_message(chat_id=chat_id, text=summary)
            raw_txt = (corrected or "").encode("utf-8")
            buf = io.BytesIO(raw_txt)
            await ptb.bot.send_document(
                chat_id=chat_id,
                document=InputFile(buf, filename="imlo_tuzatilgan.txt"),
                caption="Tuzatilgan matn (TXT)",
            )
            db_insert_action_log(int(uid), "imlo", file.filename or "upload")
        except Exception as e:
            logger.warning("spellcheck_file Telegram: %s", e)

    return out


@router.post("/api/objective")
async def api_objective(req: ObjectiveRequest):
    role = (req.role or "").strip()
    if not role:
        raise HTTPException(status_code=400, detail="Role bo'sh bo'lishi mumkin emas")
    if len(role) > 120:
        raise HTTPException(status_code=400, detail="Role juda uzun")
    if req.extra and len(req.extra) > 800:
        raise HTTPException(status_code=400, detail="Qo'shimcha ma'lumot juda uzun")

    try:
        from bot.services.ai_service import generate_objective

        text = await generate_objective(
            role=role,
            experience=req.experience,
            extra=req.extra or "",
            lang=req.lang or "uz",
        )
        if not text or text.startswith("AI model"):
            raise HTTPException(status_code=502, detail=text or "AI javobi bo'sh")
        if text.startswith("Xatolik"):
            raise HTTPException(status_code=502, detail=text)
        return {"ok": True, "text": text}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Objective API error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Objective server xatosi: {str(e)[:200]}")
