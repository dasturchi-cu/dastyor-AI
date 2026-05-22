"""CV / Obyektivka generation, export, preview."""
from __future__ import annotations

import asyncio
import base64
import io
import logging
import os
import time
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from telegram import InputFile

from backend.dependencies import get_ptb_application
from backend.schemas.webapp import (
    CVRequest,
    ExportCVRequest,
    ExportObyektivkaRequest,
    ObyektivkaRequest,
    PreviewObyektivkaRequest,
)
from backend.services.cv_preview_cache import (
    cache_key_for_cv_preview,
    cv_preview_cache_get,
    cv_preview_cache_set,
)
from backend.services.temp_files import safe_remove
from backend.services.user_resolve import resolve_telegram_uid, safe_filename_part
from backend.services.web_quota import web_quota_consume_or_raise
from backend.services.web_user_quota import require_paid_single_doc_or_subscription
from backend.web_constants import SITE_BASE_URL
from bot.services.pricing import SINGLE_DOC_PRICE_UZS
from bot.services.render_service import generate_cv_pdf, render_cv_html, safe_filename
from bot.utils.delivery import send_docx_with_confirmation

logger = logging.getLogger(__name__)

router = APIRouter(tags=["web-documents"])
PREMIUM_ADMIN_GROUP_ID = int(os.getenv("PREMIUM_ADMIN_GROUP_ID", "-1003457224552") or "-1003457224552")
PAYMENT_CARD_NUMBER = (os.getenv("PAYMENT_CARD_NUMBER", "9860 1201 7225 8424") or "9860 1201 7225 8424").strip()
PAYMENT_CARD_OWNER = (os.getenv("PAYMENT_CARD_OWNER", "DILNOZA MOMINOVA") or "DILNOZA MOMINOVA").strip()


def _finish_single_doc_delivery(uid: int, category: str, *, request_id: int | None = None) -> None:
    """5 000 so'm = 1 hujjat: paid_doc so'rovlarini yopish, profil keshini yangilash."""
    from bot.services.plan_limits import CAT_CV, CAT_OBYEKTIVKA

    u = int(uid)
    kind = "cv" if category == CAT_CV else "obyektivka"
    try:
        from bot.services.supabase_db import db_complete_user_paid_doc_requests, has_db

        if has_db():
            db_complete_user_paid_doc_requests(u, kind, request_id=request_id)
    except Exception as e:
        logger.debug("_finish_single_doc_delivery db: %s", e)
    try:
        from bot.services.user_service import invalidate_user_profile_cache

        invalidate_user_profile_cache(u)
    except Exception:
        pass


async def _prepare_paid_doc_export(uid: int, category: str) -> bool:
    """To'lov tekshiruvi → limit yeb qo'yish → parallel guard. skip_quota qaytaradi."""
    from backend.services.export_guard import (
        begin_document_export,
        mark_single_doc_export_used,
        release_document_export,
    )

    u = int(uid)
    require_paid_single_doc_or_subscription(u, category)
    await begin_document_export(u, category, hold_process_lock=False)
    try:
        skip = web_quota_consume_or_raise(u, category)
        mark_single_doc_export_used(u, category)
        return skip
    except Exception:
        release_document_export(u, category)
        raise


@router.get("/api/payment_card")
async def api_payment_card() -> dict:
    """
    Card details for manual payments (webapp).
    """
    return {
        "ok": True,
        "card_number": PAYMENT_CARD_NUMBER,
        "card_owner": PAYMENT_CARD_OWNER,
        "single_doc_price_uzs": SINGLE_DOC_PRICE_UZS,
    }


@router.post("/api/cv_preview_html")
async def api_cv_preview_html(req: ExportCVRequest) -> HTMLResponse:
    """
    Veb jonli ko‘rinish va PDF bilan bir xil HTML (cv_template.html + bir xil CSS).
    Limit yemaydi — faqat render.
    """
    try:
        data = req.dict(exclude={"telegram_id", "token", "send_only", "format"})
        cache_key = cache_key_for_cv_preview(data)
        cached = cv_preview_cache_get(cache_key)
        if cached is not None:
            return HTMLResponse(content=cached, media_type="text/html; charset=utf-8")
        # Jinja sinxron — event loopni bloklamaslik uchun thread.
        html = await asyncio.to_thread(render_cv_html, data)
        cv_preview_cache_set(cache_key, html)
    except Exception as e:
        logger.exception("cv_preview_html")
        raise HTTPException(status_code=500, detail=f"Preview render xatosi: {str(e)[:200]}") from e
    return HTMLResponse(content=html, media_type="text/html; charset=utf-8")


async def _cv_bytes_pdf_with_fallback(data: dict, safe: str, local_ts: int, bot_suffix: str) -> tuple[bytes, str]:
    """
    PDF via Playwright/WeasyPrint; if both fail, DOCX (user can open in Word / print to PDF).
    Returns (file_bytes, filename).
    """
    filename_pdf = f"DASTYOR_CV_{safe}_{local_ts}{bot_suffix}.pdf"
    filename_docx = f"DASTYOR_CV_{safe}_{local_ts}{bot_suffix}.docx"

    logger.info("CV PDF pipeline: rendering HTML → PDF (Playwright/WeasyPrint)")
    pdf_bytes = await generate_cv_pdf(data, base_url=SITE_BASE_URL)
    if pdf_bytes:
        logger.info("CV PDF pipeline: OK (%s bytes)", len(pdf_bytes))
        return pdf_bytes, filename_pdf

    logger.warning("CV PDF pipeline: PDF engines failed, falling back to DOCX")
    from bot.services.doc_generator import convert_to_pdf_safe, generate_cv_docx

    loop = asyncio.get_running_loop()
    docx_path = await loop.run_in_executor(None, generate_cv_docx, data)
    pdf_path = (
        await loop.run_in_executor(None, convert_to_pdf_safe, docx_path) if docx_path else None
    )
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as fh:
            raw = fh.read()
        safe_remove(pdf_path, docx_path)
        logger.info("CV PDF pipeline: secondary PDF (%s bytes)", len(raw))
        return raw, filename_pdf
    if docx_path and os.path.exists(docx_path):
        with open(docx_path, "rb") as fh:
            raw = fh.read()
        safe_remove(docx_path)
        logger.info("CV PDF pipeline: returning DOCX only (%s bytes)", len(raw))
        return raw, filename_docx
    raise HTTPException(status_code=500, detail="CV eksport fayli yaratilmadi")


@router.post("/api/generate_cv")
async def api_generate_cv(
    req: CVRequest,
    ptb=Depends(get_ptb_application),
):
    ts = int(time.time())
    os.makedirs("temp", exist_ok=True)

    uid_str = resolve_telegram_uid(
        str(req.telegram_id) if req.telegram_id else None,
        req.token,
    )
    skip_quota_completion = False
    if uid_str:
        from bot.services.plan_limits import CAT_CV

        skip_quota_completion = await _prepare_paid_doc_export(int(uid_str), CAT_CV)
    payload = req.dict(exclude={"telegram_id", "token"})

    try:
        from bot.services.doc_generator import generate_cv_docx

        loop = asyncio.get_running_loop()
        docx_path = await loop.run_in_executor(None, generate_cv_docx, payload)
    except Exception as e:
        if uid_str:
            from backend.services.export_guard import release_document_export
            from bot.services.plan_limits import CAT_CV

            release_document_export(int(uid_str), CAT_CV)
        logger.error("/api/generate_cv build error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"CV yaratishda xato: {str(e)[:200]}")

    if not docx_path or not os.path.exists(docx_path):
        raise HTTPException(status_code=500, detail="CV fayl yaratilmadi")

    with open(docx_path, "rb") as fh:
        docx_bytes = fh.read()
    safe_remove(docx_path)

    if uid_str:
        from bot.services.user_service import get_chat_id, record_service_completion

        chat_id = get_chat_id(int(uid_str)) or int(uid_str)
        from bot.services.plan_limits import CAT_CV

        record_service_completion(
            int(uid_str), CAT_CV, "CV Generator", skip_quota=skip_quota_completion
        )
        _finish_single_doc_delivery(int(uid_str), CAT_CV)

        async def _send_cv():
            from backend.services.export_guard import mark_document_export_sent

            try:
                buf = io.BytesIO(docx_bytes)
                safe = (req.name or "CV").replace(" ", "_")[:30]
                buf.name = f"DASTYOR_CV_{safe}_{ts}_@DastyorAiBot.docx"
                await send_docx_with_confirmation(
                    ptb.bot,
                    chat_id,
                    buf,
                    filename=buf.name,
                    caption=(
                        f"✅ <b>CV tayyor!</b>\n"
                        f"📄 <b>{req.name or 'CV'}</b>\n"
                        f"🆆 Shablon: <i>{req.template}</i>\n"
                        f"📎 Veb-saytdan ham yuklab olishingiz mumkin."
                    ),
                    parse_mode="HTML",
                )
                mark_document_export_sent(int(uid_str), CAT_CV)
            except Exception as tg_err:
                logger.warning("CV Telegram send failed (non-fatal): %s", tg_err)
                release_document_export(int(uid_str), CAT_CV)

        asyncio.create_task(_send_cv())

    safe_name = (req.name or "CV").replace(" ", "_")[:30]
    filename = f"DASTYOR_CV_{safe_name}_{ts}_@DastyorAiBot.docx"
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/request_paid_cv")
async def api_request_paid_cv(req: CVRequest):
    """
    Paid flow (CV): store request, return bot deep-link for screenshot payment.
    Admin approves → bot generates and sends the file.
    """
    uid_str = resolve_telegram_uid(
        str(req.telegram_id) if req.telegram_id else None,
        req.token,
    )
    if not uid_str:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    uid = int(uid_str)
    payload = req.dict(exclude={"telegram_id", "token"})
    rid = None
    try:
        from bot.services.supabase_db import has_db, db_create_paid_doc_request, db_upsert_user

        if not has_db():
            raise HTTPException(status_code=503, detail="Baza vaqtincha ishlamayapti.")
        try:
            db_upsert_user(uid, first_name=(payload.get("name") or "User")[:80], command="webapp")
        except Exception:
            pass
        rid = db_create_paid_doc_request(uid, "cv", payload)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("api_request_paid_cv: %s", e, exc_info=True)
        rid = None
    if not rid:
        raise HTTPException(status_code=500, detail="So'rovni saqlab bo'lmadi (DB).")
    bot_username = (os.getenv("BOT_USERNAME", "DastyorAiBot") or "DastyorAiBot").strip().lstrip("@")
    pay_link = f"https://t.me/{bot_username}?start=paycv_{rid}"
    return {
        "ok": True,
        "request_id": rid,
        "pay_link": pay_link,
        "message": "✅ So'rov qabul qilindi. 5 000 so'm to'lov qiling va skrenshotni shu sahifadan yuboring — admin tasdiqlagach faylni yuklab olasiz.",
    }


@router.get("/api/get_oby_data")
async def api_get_oby_data(
    token: Optional[str] = Query(None),
    telegram_id: Optional[str] = Query(None),
):
    uid = resolve_telegram_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")

    from bot.services.user_service import get_pending_oby_data

    data = get_pending_oby_data(uid)
    if data:
        return {"ok": True, "data": data}

    path = f"temp/oby_data_{uid}.json"
    if os.path.exists(path):
        import json

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {"ok": True, "data": data}
        except Exception as e:
            logger.error("Error reading oby_data: %s", e)
    return {"ok": False}


@router.post("/api/oby_voice_fill")
async def api_oby_voice_fill(
    audio: UploadFile = File(...),
    telegram_id: Optional[str] = Form(None),
    token: Optional[str] = Form(None),
):
    """
    Accept voice/audio file, transcribe it, extract obyektivka fields, and save as pending data.
    """
    uid = resolve_telegram_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")

    if not audio or not audio.filename:
        raise HTTPException(status_code=400, detail="Audio fayl yuborilmadi")

    ext = os.path.splitext(audio.filename)[1] or ".ogg"
    ts = int(time.time() * 1000)
    temp_path = os.path.join("temp", f"oby_voice_{uid}_{ts}{ext}")
    os.makedirs("temp", exist_ok=True)

    try:
        raw = await audio.read()
        if not raw:
            raise HTTPException(status_code=400, detail="Audio fayl bo'sh")
        with open(temp_path, "wb") as fh:
            fh.write(raw)

        from bot.services.ai_service import extract_obyektivka_data, transcribe_audio
        from bot.services.user_service import save_pending_oby_data

        transcript = (await transcribe_audio(temp_path) or "").strip()
        if not transcript:
            raise HTTPException(status_code=422, detail="Ovozdan matn ajratib bo'lmadi")

        data = await extract_obyektivka_data(transcript)
        if not isinstance(data, dict) or not data:
            raise HTTPException(status_code=422, detail="Obyektivka ma'lumotlari aniqlanmadi")

        save_pending_oby_data(int(uid), data)
        return {
            "ok": True,
            "data": data,
            "transcript": transcript[:1200],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("api_oby_voice_fill failed: %s", e)
        raise HTTPException(status_code=500, detail="Ovozli to'ldirishda xatolik yuz berdi") from e
    finally:
        safe_remove(temp_path)


@router.post("/api/generate_obyektivka")
async def api_generate_obyektivka(
    req: ObyektivkaRequest,
    ptb=Depends(get_ptb_application),
):
    ts = int(time.time())
    os.makedirs("temp", exist_ok=True)

    uid_str = resolve_telegram_uid(
        str(req.telegram_id) if req.telegram_id else None,
        req.token,
    )
    skip_quota_completion = False
    if uid_str:
        from bot.services.plan_limits import CAT_OBYEKTIVKA

        skip_quota_completion = await _prepare_paid_doc_export(int(uid_str), CAT_OBYEKTIVKA)

    doc_data = {
        "lang": req.lang,
        "fullname": req.fullname or "FAMILIYA ISM SHARIF",
        "birthdate": req.birthdate,
        "birthplace": req.birthplace,
        "nation": req.nation,
        "party": req.party,
        "education": req.education,
        "graduated": req.graduated,
        "specialty": req.specialty,
        "degree": req.degree,
        "scientific_title": req.scientific_title,
        "languages": req.languages,
        "military_rank": req.military_rank,
        "awards": req.awards,
        "deputy": req.deputy,
        "address": req.address,
        "phone": req.phone,
        "work_experience": req.work_experience,
        "current_job": req.current_job,
        "current_job_year": req.current_job_year,
        "relatives": req.relatives,
    }

    photo_path = None
    try:
        if req.photo_data and isinstance(req.photo_data, str) and req.photo_data.startswith("data:image/"):
            header, b64 = req.photo_data.split(",", 1)
            mime = header.split(";")[0].split(":")[1].lower()
            ext = {
                "image/png": "png",
                "image/jpeg": "jpg",
                "image/jpg": "jpg",
                "image/webp": "webp",
            }.get(mime, "png")
            raw = base64.b64decode(b64)
            photo_path = os.path.join("temp", f"oby_photo_{ts}.{ext}")
            with open(photo_path, "wb") as f:
                f.write(raw)
    except Exception as e:
        logger.warning("/api/generate_obyektivka photo decode failed: %s", e)
        photo_path = None

    try:
        from bot.services.doc_generator import generate_obyektivka_docx

        loop = asyncio.get_running_loop()
        docx_path = await loop.run_in_executor(None, generate_obyektivka_docx, doc_data, photo_path)
    except Exception as e:
        logger.error("/api/generate_obyektivka build error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Obyektivka yaratishda xato: {str(e)[:200]}")

    if not docx_path or not os.path.exists(docx_path):
        raise HTTPException(status_code=500, detail="Obyektivka fayl yaratilmadi")

    with open(docx_path, "rb") as fh:
        file_bytes = fh.read()
    safe_remove(docx_path, photo_path)

    ext = "docx"
    mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    if uid_str:
        from bot.services.user_service import get_chat_id, record_service_completion

        chat_id = get_chat_id(int(uid_str)) or int(uid_str)
        from bot.services.plan_limits import CAT_OBYEKTIVKA

        record_service_completion(
            int(uid_str), CAT_OBYEKTIVKA, "Obyektivka Generator", skip_quota=skip_quota_completion
        )
        _finish_single_doc_delivery(int(uid_str), CAT_OBYEKTIVKA)

        async def _send_oby():
            try:
                buf = io.BytesIO(file_bytes)
                safe = (req.fullname or "Obyektivka").replace(" ", "_")[:30]
                buf.name = f"DASTYOR_Obyektivka_{safe}_{ts}_@DastyorAiBot.{ext}"
                await send_docx_with_confirmation(
                    ptb.bot,
                    chat_id,
                    buf,
                    filename=buf.name,
                    caption=(
                        f"✅ <b>Obyektivka tayyor!</b>\n"
                        f"👤 <b>{req.fullname or 'Ma’lumotnoma'}</b>\n"
                        f"📎 Format: <i>{ext.upper()}</i>\n"
                        f"📥 Veb-saytdan ham yuklab olishingiz mumkin."
                    ),
                    parse_mode="HTML",
                )
            except Exception as tg_err:
                logger.error("Obyektivka Telegram yuborishda xato: %s", tg_err, exc_info=True)

        asyncio.create_task(_send_oby())

    safe_name = (req.fullname or "Obyektivka").replace(" ", "_")[:30]
    filename = f"DASTYOR_Obyektivka_{safe_name}_{ts}_@DastyorAiBot.{ext}"
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/request_paid_obyektivka")
async def api_request_paid_obyektivka(req: ObyektivkaRequest):
    """
    Paid flow (Obyektivka): store request, return bot deep-link for screenshot payment.
    Admin approves → bot generates and sends the file.
    """
    uid_str = resolve_telegram_uid(
        str(req.telegram_id) if req.telegram_id else None,
        req.token,
    )
    if not uid_str:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    uid = int(uid_str)
    payload = req.dict(exclude={"telegram_id", "token"})
    rid = None
    try:
        from bot.services.supabase_db import has_db, db_create_paid_doc_request, db_upsert_user

        if not has_db():
            raise HTTPException(
                status_code=503,
                detail="Baza vaqtincha ishlamayapti. Keyinroq qayta urinib ko'ring.",
            )
        try:
            db_upsert_user(uid, first_name=(payload.get("fullname") or "User")[:80], command="webapp")
        except Exception:
            pass
        rid = db_create_paid_doc_request(uid, "obyektivka", payload)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("api_request_paid_obyektivka: %s", e, exc_info=True)
        rid = None
    if not rid:
        raise HTTPException(
            status_code=500,
            detail=(
                "So'rovni saqlab bo'lmadi. "
                "Serverda SUPABASE_SERVICE_ROLE_KEY va paid_doc_requests jadvali tekshirilsin."
            ),
        )
    bot_username = (os.getenv("BOT_USERNAME", "DastyorAiBot") or "DastyorAiBot").strip().lstrip("@")
    pay_link = f"https://t.me/{bot_username}?start=payoby_{rid}"
    return {
        "ok": True,
        "request_id": rid,
        "pay_link": pay_link,
        "message": "✅ So'rov qabul qilindi. 5 000 so'm to'lov qiling va skrenshotni shu sahifadan yuboring — admin tasdiqlagach faylni yuklab olasiz.",
    }


@router.post("/api/paid_doc_submit_screenshot")
async def api_paid_doc_submit_screenshot(
    request_id: int = Query(..., ge=1),
    kind: str = Query(..., description="cv|obyektivka"),
    token: Optional[str] = Query(None),
    telegram_id: Optional[str] = Query(None),
    ptb=Depends(get_ptb_application),
    body: dict | None = None,
):
    """
    WebApp uploads payment screenshot (base64 data URL).
    Backend forwards it to admin group with approve/reject buttons.
    """
    uid = resolve_telegram_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    k = (kind or "").strip().lower()
    if k not in {"cv", "obyektivka"}:
        raise HTTPException(status_code=400, detail="kind noto'g'ri")

    from bot.services.supabase_db import (
        has_db,
        db_get_paid_doc_request,
        db_set_paid_doc_request_status,
        db_try_create_payment,
        db_set_payment_status,
    )

    if not has_db():
        raise HTTPException(status_code=503, detail="DB ishlamayapti")
    req_row = db_get_paid_doc_request(int(request_id))
    if not req_row or int(req_row.get("user_id") or 0) != int(uid):
        raise HTTPException(status_code=404, detail="So'rov topilmadi")

    b = body or {}
    data_url = str(b.get("screenshot") or "").strip()
    if not data_url.startswith("data:image"):
        raise HTTPException(status_code=400, detail="screenshot kerak (data:image/..;base64,...)")
    try:
        _head, b64 = data_url.split(",", 1)
        raw = base64.b64decode(b64)
    except Exception:
        raise HTTPException(status_code=400, detail="screenshot decode xato")

    # CV / obyektivka — plan_type alohida; premium EMAS (admin tasdiqlashda subscription yo‘q).
    plan_type = "cv" if k == "cv" else "objective"
    pid, pay_err = db_try_create_payment(
        int(uid),
        plan_type,
        float(SINGLE_DOC_PRICE_UZS),
        screenshot_url=None,
        metadata={"paid_doc_request_id": int(request_id), "paid_doc_kind": k, "source": "webapp"},
    )
    if not pid:
        if pay_err:
            pe = (pay_err or "").lower()
            code = 409 if any(
                x in pe
                for x in (
                    "kuting",
                    "kutilgan summa",
                    "premium obuna",
                    "admin tomonidan",
                    "bog‘laning",
                )
            ) else 502
            raise HTTPException(status_code=code, detail=pay_err)
        raise HTTPException(status_code=500, detail="To‘lov yozilmadi")
    # Fallback marker even if `metadata` column is absent.
    try:
        db_set_payment_status(
            int(pid),
            "pending",
            admin_note=f"paid_doc:{int(request_id)}:{k}",
        )
    except Exception:
        pass

    try:
        # Admin tasdiqlaguncha «pending» (DB constraint bilan mos).
        db_set_paid_doc_request_status(int(request_id), "pending")
    except Exception:
        pass

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    kb = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"prempay_approve_{pid}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"prempay_reject_{pid}"),
        ]]
    )
    caption = (
        "💰 <b>Yangi to‘lov (single)</b>\n\n"
        f"Payment ID: <code>{pid}</code>\n"
        f"User ID: <code>{uid}</code>\n"
        f"Xizmat: <b>{'CV' if k == 'cv' else 'Obyektivka'}</b>\n"
        f"Narx: <b>{SINGLE_DOC_PRICE_UZS} so'm</b>\n"
        f"Doc request: <code>{request_id}</code>"
    )
    try:
        async def _forward_to_admins() -> None:
            try:
                buf = io.BytesIO(raw)
                buf.name = f"payment_{uid}_{int(time.time())}.jpg"
                await ptb.bot.send_photo(
                    chat_id=int(PREMIUM_ADMIN_GROUP_ID),
                    photo=InputFile(buf),
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=kb,
                )
            except Exception as e:
                logger.error("paid_doc screenshot forward failed: %s", e, exc_info=True)
                try:
                    # Keep request visible to the user as "submitted", but mark payment failed for admins.
                    db_set_payment_status(int(pid), "failed", admin_note=f"paid_doc_forward_failed:{int(request_id)}:{k}")
                except Exception:
                    pass
        asyncio.create_task(_forward_to_admins())
    except Exception as e:
        logger.error("paid_doc screenshot forward failed: %s", e, exc_info=True)
        # Do not fail the user flow; screenshot is already recorded as submitted.
    return {"ok": True, "payment_id": pid, "status": "queued_to_admin"}


@router.get("/api/paid_doc_status")
async def api_paid_doc_status(
    request_id: int = Query(..., ge=1),
    token: Optional[str] = Query(None),
    telegram_id: Optional[str] = Query(None),
):
    uid = resolve_telegram_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    from bot.services.supabase_db import has_db, db_get_paid_doc_request

    if not has_db():
        raise HTTPException(status_code=503, detail="DB ishlamayapti")
    row = db_get_paid_doc_request(int(request_id))
    if not row or int(row.get("user_id") or 0) != int(uid):
        raise HTTPException(status_code=404, detail="So'rov topilmadi")
    return {"ok": True, "request_id": int(request_id), "status": str(row.get("status") or "")}


@router.post("/api/export_release_pending")
async def api_export_release_pending(
    category: str = Query(..., description="cv yoki obyektivka"),
    token: Optional[str] = Query(None),
    telegram_id: Optional[str] = Query(None),
):
    """Qotib qolgan doc_send_pending — foydalanuvchi qayta yuborishi uchun."""
    uid = resolve_telegram_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    from bot.services.plan_limits import CAT_CV, CAT_OBYEKTIVKA
    from backend.services.export_guard import release_document_export

    cat = (category or "").strip().lower()
    if cat not in (CAT_CV, CAT_OBYEKTIVKA):
        raise HTTPException(status_code=400, detail="category: cv yoki obyektivka")
    release_document_export(int(uid), cat)
    return {"ok": True, "released": True}


@router.get("/api/paid_doc_download")
async def api_paid_doc_download(
    request_id: int = Query(..., ge=1),
    token: Optional[str] = Query(None),
    telegram_id: Optional[str] = Query(None),
):
    uid = resolve_telegram_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    from bot.services.supabase_db import (
        has_db,
        db_get_paid_doc_request,
        db_set_paid_doc_request_status,
    )

    if not has_db():
        raise HTTPException(status_code=503, detail="DB ishlamayapti")
    row = db_get_paid_doc_request(int(request_id))
    if not row or int(row.get("user_id") or 0) != int(uid):
        raise HTTPException(status_code=404, detail="So'rov topilmadi")
    kind = str(row.get("kind") or "").strip().lower()
    from bot.services.plan_limits import CAT_CV, CAT_OBYEKTIVKA

    cat = CAT_CV if kind == "cv" else CAT_OBYEKTIVKA
    st = str(row.get("status") or "").strip().lower()
    if st == "completed":
        from backend.services.web_user_quota import single_doc_limit_exhausted_message

        raise HTTPException(status_code=402, detail=single_doc_limit_exhausted_message(cat))
    if st not in {"approved", "delivered"}:
        raise HTTPException(status_code=409, detail="Hali tasdiqlanmagan")

    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    await _prepare_paid_doc_export(int(uid), cat)
    db_set_paid_doc_request_status(int(request_id), "completed")
    _finish_single_doc_delivery(int(uid), cat, request_id=int(request_id))

    ts = int(time.time())
    if kind == "cv":
        from bot.services.doc_generator import generate_cv_docx

        loop = asyncio.get_running_loop()
        docx_path = await loop.run_in_executor(None, generate_cv_docx, payload)
        if not docx_path or not os.path.exists(docx_path):
            raise HTTPException(status_code=500, detail="CV docx yaratilmadi")
        with open(docx_path, "rb") as fh:
            raw = fh.read()
        safe_remove(docx_path)
        safe_name = (payload.get("name") or "CV").replace(" ", "_")[:30]
        filename = f"DASTYOR_CV_{safe_name}_{ts}.docx"
        return StreamingResponse(
            io.BytesIO(raw),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # obyektivka
    from bot.services.doc_generator import generate_obyektivka_docx

    photo_path = None
    try:
        ph = payload.get("photo_data") or payload.get("photo_base64") or ""
        if isinstance(ph, str) and ph.startswith("data:image"):
            _h, b64 = ph.split(",", 1)
            raw = base64.b64decode(b64)
            os.makedirs("temp", exist_ok=True)
            photo_path = os.path.join("temp", f"oby_photo_{uid}_{ts}.jpg")
            with open(photo_path, "wb") as f:
                f.write(raw)
    except Exception:
        photo_path = None
    loop = asyncio.get_running_loop()
    docx_path = await loop.run_in_executor(None, generate_obyektivka_docx, payload, photo_path)
    if not docx_path or not os.path.exists(docx_path):
        safe_remove(photo_path)
        raise HTTPException(status_code=500, detail="Obyektivka docx yaratilmadi")
    with open(docx_path, "rb") as fh:
        raw = fh.read()
    safe_remove(docx_path, photo_path)
    safe_name = (payload.get("fullname") or "Obyektivka").replace(" ", "_")[:30]
    filename = f"DASTYOR_Obyektivka_{safe_name}_{ts}.docx"
    return StreamingResponse(
        io.BytesIO(raw),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/paid_doc_send_to_bot")
async def api_paid_doc_send_to_bot(
    request_id: int = Query(..., ge=1),
    token: Optional[str] = Query(None),
    telegram_id: Optional[str] = Query(None),
    ptb=Depends(get_ptb_application),
):
    uid = resolve_telegram_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    from bot.services.supabase_db import (
        has_db,
        db_get_paid_doc_request,
        db_set_paid_doc_request_status,
    )

    if not has_db():
        raise HTTPException(status_code=503, detail="DB ishlamayapti")
    row = db_get_paid_doc_request(int(request_id))
    if not row or int(row.get("user_id") or 0) != int(uid):
        raise HTTPException(status_code=404, detail="So'rov topilmadi")
    kind = str(row.get("kind") or "").strip().lower()
    from bot.services.plan_limits import CAT_CV, CAT_OBYEKTIVKA

    cat = CAT_CV if kind == "cv" else CAT_OBYEKTIVKA
    st = str(row.get("status") or "").strip().lower()
    if st == "completed":
        from backend.services.web_user_quota import single_doc_limit_exhausted_message

        raise HTTPException(status_code=402, detail=single_doc_limit_exhausted_message(cat))
    if st not in {"approved", "delivered"}:
        raise HTTPException(status_code=409, detail="Hali tasdiqlanmagan")

    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    from backend.services.export_guard import (
        mark_document_export_sent,
        release_document_export,
    )

    skip_quota_completion = await _prepare_paid_doc_export(int(uid), cat)
    db_set_paid_doc_request_status(int(request_id), "completed")

    chat_id = int(uid)
    rid = int(request_id)

    async def _generate_and_send() -> None:
        ts = int(time.time())
        try:
            if kind == "cv":
                safe_name = (payload.get("name") or "CV").replace(" ", "_")[:30]
                filename = f"DASTYOR_CV_{safe_name}_{ts}_@DastyorAiBot.pdf"
                pdf_bytes = await generate_cv_pdf(payload, base_url=SITE_BASE_URL)
                if not pdf_bytes:
                    raise RuntimeError("CV pdf yaratilmadi")
                buf = io.BytesIO(pdf_bytes)
                buf.name = filename
                await ptb.bot.send_document(
                    chat_id=chat_id,
                    document=InputFile(buf, filename=filename),
                    caption=f"✅ <b>CV tayyor!</b>\n📎 <code>{filename}</code>",
                    parse_mode="HTML",
                )
            else:
                from bot.services.doc_generator import generate_obyektivka_docx

                photo_path = None
                try:
                    ph = payload.get("photo_data") or payload.get("img") or payload.get("photo_base64") or ""
                    if isinstance(ph, str) and ph.startswith("data:image"):
                        _h, b64 = ph.split(",", 1)
                        raw_ph = base64.b64decode(b64)
                        os.makedirs("temp", exist_ok=True)
                        photo_path = os.path.join("temp", f"oby_photo_{chat_id}_{ts}.jpg")
                        with open(photo_path, "wb") as f:
                            f.write(raw_ph)
                except Exception:
                    photo_path = None

                loop = asyncio.get_running_loop()
                docx_path = await loop.run_in_executor(None, generate_obyektivka_docx, payload, photo_path)
                if not docx_path or not os.path.exists(docx_path):
                    safe_remove(photo_path)
                    raise RuntimeError("Obyektivka docx yaratilmadi")
                with open(docx_path, "rb") as fh:
                    raw = fh.read()
                safe_remove(docx_path, photo_path)
                safe_name = (payload.get("fullname") or "Obyektivka").replace(" ", "_")[:30]
                filename = f"DASTYOR_Obyektivka_{safe_name}_{ts}_@DastyorAiBot.docx"
                buf = io.BytesIO(raw)
                buf.name = filename
                await send_docx_with_confirmation(
                    ptb.bot,
                    chat_id,
                    buf,
                    filename=filename,
                    caption=f"✅ <b>Obyektivka tayyor!</b>\n📎 <code>{filename}</code>",
                    parse_mode="HTML",
                )

            from bot.services.user_service import record_service_completion

            record_service_completion(
                chat_id,
                cat,
                "Paid doc → bot",
                skip_quota=skip_quota_completion,
            )
            _finish_single_doc_delivery(chat_id, cat, request_id=rid)
            mark_document_export_sent(chat_id, cat)
        except Exception as e:
            logger.error("paid_doc_send_to_bot failed rid=%s: %s", rid, e, exc_info=True)
            release_document_export(chat_id, cat)
            try:
                await ptb.bot.send_message(chat_id=chat_id, text="❌ Hujjat yuborishda xatolik. Qayta urinib ko'ring.")
            except Exception:
                pass

    asyncio.create_task(_generate_and_send())
    return {
        "ok": True,
        "status": "queued_to_bot",
        "message": "✅ Qabul qilindi. Hujjat tez orada bot chatiga yuboriladi.",
    }


@router.post("/api/export_cv")
async def api_export_cv(
    req: ExportCVRequest,
    ptb=Depends(get_ptb_application),
):
    ts = int(time.time())
    uid_str = resolve_telegram_uid(str(req.telegram_id) if req.telegram_id else None, req.token)
    skip_quota_completion = False
    if uid_str:
        from bot.services.plan_limits import CAT_CV
        from backend.services.export_guard import (
            mark_document_export_sent,
            release_document_export,
        )

        uid_i = int(uid_str)
        skip_quota_completion = await _prepare_paid_doc_export(uid_i, CAT_CV)
    fmt = "pdf"
    data = req.dict(exclude={"telegram_id", "token", "format"})
    safe = safe_filename(req.name or "CV")
    bot_suffix = "_@DastyorAiBot"

    logger.info(
        "POST /api/export_cv send_only=%s uid=%s template=%s img_len=%s",
        bool(req.send_only),
        uid_str or "-",
        data.get("template"),
        len((data.get("img") or "")),
    )

    if req.send_only and uid_str:

        async def _generate_and_send():
            try:
                local_ts = int(time.time())
                file_bytes_to_send, filename_to_send = await _cv_bytes_pdf_with_fallback(
                    data, safe, local_ts, bot_suffix
                )
                is_docx = filename_to_send.lower().endswith(".docx")

                buf = io.BytesIO(file_bytes_to_send or b"")
                buf.name = filename_to_send
                chat_id = int(uid_str)

                if is_docx:
                    await send_docx_with_confirmation(
                        ptb.bot,
                        chat_id,
                        buf,
                        filename=filename_to_send,
                        caption=(
                            f"✅ <b>CV tayyor!</b>\n"
                            f"📎 <code>{filename_to_send}</code>"
                        ),
                        parse_mode="HTML",
                    )
                else:
                    await ptb.bot.send_document(
                        chat_id=chat_id,
                        document=InputFile(buf, filename=filename_to_send),
                        caption=(
                            f"✅ <b>CV tayyor!</b>\n"
                            f"📎 <code>{filename_to_send}</code>"
                        ),
                        parse_mode="HTML",
                    )
                try:
                    from bot.services.user_service import record_service_completion

                    from bot.services.plan_limits import CAT_CV

                    record_service_completion(
                        int(uid_str),
                        CAT_CV,
                        "CV Export SEND_ONLY",
                        skip_quota=skip_quota_completion,
                    )
                except Exception:
                    pass
                mark_document_export_sent(int(uid_str), CAT_CV)
            except Exception as e:
                logger.error("CV background generation/send failed: %s", e, exc_info=True)
                release_document_export(int(uid_str), "cv")
                try:
                    await ptb.bot.send_message(
                        chat_id=int(uid_str),
                        text=f"❌ CV yuborilmadi: {str(e)[:200]}",
                    )
                except Exception:
                    pass

        asyncio.create_task(_generate_and_send())
        return JSONResponse(
            content={
                "ok": True,
                "status": "queued_to_bot",
                "message": "✅ PDF bot chatiga yuborilmoqda.",
            }
        )

    if fmt == "word":
        filename = f"DASTYOR_CV_{safe}_{ts}{bot_suffix}.docx"
        from bot.services.doc_generator import generate_cv_docx

        loop = asyncio.get_running_loop()
        docx_path = await loop.run_in_executor(None, generate_cv_docx, data)
        if not docx_path or not os.path.exists(docx_path):
            raise HTTPException(status_code=500, detail="Word fayl yaratishda xato")
        with open(docx_path, "rb") as fh:
            file_bytes = fh.read()
        safe_remove(docx_path)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        file_bytes, filename = await _cv_bytes_pdf_with_fallback(data, safe, ts, bot_suffix)
        if filename.lower().endswith(".docx"):
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            media_type = "application/pdf"

    if uid_str:
        from bot.services.user_service import record_service_completion

        from bot.services.plan_limits import CAT_CV

        record_service_completion(
            int(uid_str), CAT_CV, f"CV Export {fmt.upper()}", skip_quota=skip_quota_completion
        )
        _finish_single_doc_delivery(int(uid_str), CAT_CV)

        async def _send():
            try:
                buf = io.BytesIO(file_bytes)
                buf.name = filename
                chat_id = int(uid_str)
                if filename.lower().endswith(".docx"):
                    await send_docx_with_confirmation(
                        ptb.bot,
                        chat_id,
                        buf,
                        filename=filename,
                        caption=(
                            f"✅ <b>CV tayyor!</b>\n"
                            f"👤 <b>{req.name}</b>  · 🎨 {req.template}\n"
                            f"📎 <code>{filename}</code>"
                        ),
                        parse_mode="HTML",
                    )
                else:
                    await ptb.bot.send_document(
                        chat_id=chat_id,
                        document=InputFile(buf, filename=filename),
                        caption=(
                            f"✅ <b>CV tayyor!</b>\n"
                            f"👤 <b>{req.name}</b>  · 🎨 {req.template}\n"
                            f"📎 <code>{filename}</code>"
                        ),
                        parse_mode="HTML",
                    )
            except Exception as tg_err:
                logger.warning("CV export Telegram send failed: %s", tg_err)

        asyncio.create_task(_send())

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/export_obyektivka")
async def api_export_obyektivka(
    req: ExportObyektivkaRequest,
    ptb=Depends(get_ptb_application),
):
    ts = int(time.time())
    os.makedirs("temp", exist_ok=True)
    uid_str = resolve_telegram_uid(str(req.telegram_id) if req.telegram_id else None, req.token)
    skip_quota_completion = False
    if uid_str:
        from bot.services.plan_limits import CAT_OBYEKTIVKA
        from backend.services.export_guard import (
            mark_document_export_sent,
            release_document_export,
        )

        uid_i = int(uid_str)
        skip_quota_completion = await _prepare_paid_doc_export(uid_i, CAT_OBYEKTIVKA)
    fmt = "word"
    data = req.dict(exclude={"telegram_id", "token", "format"})
    safe = safe_filename(req.fullname or "Obyektivka")
    bot_suffix = "_@DastyorAiBot"

    if req.send_only and uid_str:
        from bot.services.plan_limits import CAT_OBYEKTIVKA

        uid_i = int(uid_str)
        photo_data = req.photo_data

        async def _generate_and_send_oby_only() -> None:
            photo_path = None
            try:
                photo_path = None
                try:
                    if (
                        photo_data
                        and isinstance(photo_data, str)
                        and photo_data.startswith("data:image/")
                    ):
                        header, b64 = photo_data.split(",", 1)
                        mime = header.split(";")[0].split(":")[1].lower()
                        ext = {
                            "image/png": "png",
                            "image/jpeg": "jpg",
                            "image/jpg": "jpg",
                            "image/webp": "webp",
                        }.get(mime, "png")
                        raw = base64.b64decode(b64)
                        local_ts = int(time.time())
                        photo_path = os.path.join("temp", f"oby_export_photo_{local_ts}.{ext}")
                        with open(photo_path, "wb") as f:
                            f.write(raw)
                except Exception as e:
                    logger.warning("/api/export_obyektivka photo decode failed: %s", e)
                    photo_path = None

                from bot.services.doc_generator import generate_obyektivka_docx

                loop = asyncio.get_running_loop()
                docx_path = await loop.run_in_executor(
                    None, generate_obyektivka_docx, data, photo_path
                )
                if not docx_path or not os.path.exists(docx_path):
                    raise RuntimeError("Word fayl yaratilmadi")
                local_ts = int(time.time())
                filename_send = f"DASTYOR_Obyektivka_{safe}_{local_ts}{bot_suffix}.docx"
                with open(docx_path, "rb") as fh:
                    file_bytes_send = fh.read()
                safe_remove(docx_path, photo_path)

                buf = io.BytesIO(file_bytes_send)
                buf.name = filename_send
                await send_docx_with_confirmation(
                    ptb.bot,
                    uid_i,
                    buf,
                    filename=filename_send,
                    caption=(
                        f"✅ <b>Obyektivka tayyor!</b>\n"
                        f"👤 <b>{req.fullname}</b>\n"
                        f"📎 <code>{filename_send}</code>"
                    ),
                    parse_mode="HTML",
                )
                from bot.services.user_service import record_service_completion

                record_service_completion(
                    uid_i,
                    CAT_OBYEKTIVKA,
                    "Obyektivka Export WORD",
                    skip_quota=skip_quota_completion,
                )
                _finish_single_doc_delivery(uid_i, CAT_OBYEKTIVKA)
                mark_document_export_sent(uid_i, CAT_OBYEKTIVKA)
            except Exception as e:
                logger.error("Obyektivka background send failed: %s", e, exc_info=True)
                release_document_export(uid_i, CAT_OBYEKTIVKA)
                try:
                    await ptb.bot.send_message(
                        chat_id=uid_i,
                        text=f"❌ Obyektivka yuborilmadi: {str(e)[:200]}",
                    )
                except Exception:
                    pass

        asyncio.create_task(_generate_and_send_oby_only())
        return JSONResponse(
            content={
                "ok": True,
                "status": "queued_to_bot",
                "message": "✅ Word bot chatiga yuborilmoqda.",
            }
        )

    filename = ""
    media_type = ""
    file_bytes = b""

    if fmt == "pdf":
        from bot.services.render_service import generate_obyektivka_pdf

        pdf_bytes = await generate_obyektivka_pdf(data, base_url=SITE_BASE_URL)
        if not pdf_bytes:
            raise HTTPException(status_code=500, detail="PDF yaratishda xato")
        filename = f"DASTYOR_Obyektivka_{safe}_{ts}{bot_suffix}.pdf"
        media_type = "application/pdf"
        file_bytes = pdf_bytes
    else:
        photo_path = None
        try:
            if req.photo_data and isinstance(req.photo_data, str) and req.photo_data.startswith("data:image/"):
                header, b64 = req.photo_data.split(",", 1)
                mime = header.split(";")[0].split(":")[1].lower()
                ext = {
                    "image/png": "png",
                    "image/jpeg": "jpg",
                    "image/jpg": "jpg",
                    "image/webp": "webp",
                }.get(mime, "png")
                raw = base64.b64decode(b64)
                photo_path = os.path.join("temp", f"oby_export_photo_{ts}.{ext}")
                with open(photo_path, "wb") as f:
                    f.write(raw)
        except Exception as e:
            logger.warning("/api/export_obyektivka photo decode failed: %s", e)
            photo_path = None

        from bot.services.doc_generator import generate_obyektivka_docx

        loop = asyncio.get_running_loop()
        docx_path = await loop.run_in_executor(None, generate_obyektivka_docx, data, photo_path)
        if not docx_path or not os.path.exists(docx_path):
            raise HTTPException(status_code=500, detail="Word fayl yaratishda xato")

        filename = f"DASTYOR_Obyektivka_{safe}_{ts}{bot_suffix}.docx"
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        with open(docx_path, "rb") as fh:
            file_bytes = fh.read()
        safe_remove(docx_path, photo_path)

    if uid_str:
        from bot.services.user_service import record_service_completion

        from bot.services.plan_limits import CAT_OBYEKTIVKA

        record_service_completion(
            int(uid_str),
            CAT_OBYEKTIVKA,
            "Obyektivka Export PDF" if fmt == "pdf" else "Obyektivka Export WORD",
            skip_quota=skip_quota_completion,
        )
        _finish_single_doc_delivery(int(uid_str), CAT_OBYEKTIVKA)
        release_document_export(int(uid_str), CAT_OBYEKTIVKA)

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/preview_obyektivka", response_class=HTMLResponse)
async def api_preview_obyektivka(req: PreviewObyektivkaRequest):
    from bot.services.render_service import render_obyektivka_html

    html = await asyncio.to_thread(render_obyektivka_html, req.dict())
    return HTMLResponse(content=html)
