"""Payment API routes."""
from __future__ import annotations

import asyncio
import logging
import os

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse

from backend.schemas.webapp import AuthRequest
from config.settings import settings
from core.security import allowed_image, rate_limit, validate_phone
from core.telegram_auth import extract_telegram_user_id, validate_init_data
from database.repositories import payments as payments_repo
from database.repositories import users as users_repo
from features.payment import service as payment_service
from shared import async_db
from shared.auth import is_admin, resolve_uid

logger = logging.getLogger(__name__)
router = APIRouter(tags=["payment"])


@router.get("/api/payment_card")
async def api_payment_card() -> dict:
    info = payment_service.payment_info()
    return {"ok": True, **info}


@router.get("/api/me")
async def api_me(token: str | None = Query(None), telegram_id: str | None = Query(None)) -> dict:
    uid = resolve_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    from shared.session_service import get_session_by_telegram_id
    from database.repositories import users as users_repo

    user = await async_db.run(users_repo.get_by_telegram_id, uid)
    if not user:
        user = await async_db.run(users_repo.upsert_user, uid)
    session = get_session_by_telegram_id(uid) or {}
    return {
        "ok": True,
        "telegram_id": uid,
        "first_name": session.get("first_name", user.get("first_name", "")),
        "username": session.get("username", user.get("username", "")),
        "credits": int(user.get("credits") or 0),
        "single_doc_price_uzs": settings.single_doc_price_uzs,
        "has_access": int(user.get("credits") or 0) > 0,
        "credit_note": f"Ovoz/matn bepul. Tayyor fayl: {settings.single_doc_price_uzs:,} so'm = 1 ta hujjat (CV, Obyektivka, Muqova, Tarjima)",
    }


@router.post("/api/auth")
async def api_auth(req: AuthRequest, request: Request) -> dict:
    from core.security import client_ip, rate_limit
    from core.turnstile import verify_turnstile
    from shared.security_audit import EVENT_AUTH_FAILED, EVENT_AUTH_SUCCESS, log_security_event
    from shared.session_service import create_session
    from database.repositories import users as users_repo

    await rate_limit(request)
    ip = client_ip(request)

    if settings.turnstile_secret_key:
        ok = await verify_turnstile(req.turnstile_token, remote_ip=ip)
        if not ok:
            log_security_event(EVENT_AUTH_FAILED, severity="warn", ip=ip, details="turnstile")
            raise HTTPException(status_code=403, detail="Bot tekshiruvi muvaffaqiyatsiz")

    body = req
    init_data = (body.init_data or "").strip()

    if not settings.allow_insecure_auth:
        if not init_data:
            log_security_event(EVENT_AUTH_FAILED, ip=ip, user_id=body.telegram_id, details="no_init_data")
            raise HTTPException(status_code=401, detail="init_data talab qilinadi")
        validated = validate_init_data(
            init_data,
            settings.bot_token,
            max_age_seconds=settings.init_data_max_age_seconds,
        )
        if not validated:
            log_security_event(EVENT_AUTH_FAILED, ip=ip, user_id=body.telegram_id, details="bad_init_data")
            raise HTTPException(status_code=401, detail="init_data noto'g'ri yoki muddati o'tgan")
        verified_id = extract_telegram_user_id(validated)
        if not verified_id or int(verified_id) != int(body.telegram_id):
            log_security_event(EVENT_AUTH_FAILED, ip=ip, user_id=body.telegram_id, details="id_mismatch")
            raise HTTPException(status_code=401, detail="Foydalanuvchi tasdiqlanmadi")

    await async_db.run(
        users_repo.upsert_user,
        body.telegram_id,
        username=body.username,
        first_name=body.first_name,
    )
    token = await async_db.run(
        create_session,
        telegram_id=body.telegram_id,
        first_name=body.first_name,
        username=body.username,
        photo_url=body.photo_url,
    )
    log_security_event(EVENT_AUTH_SUCCESS, ip=ip, user_id=body.telegram_id)
    return {"ok": True, "token": token, "telegram_id": body.telegram_id}


@router.post("/api/submit_payment")
async def api_submit_payment(
    request: Request,
    payer_name: str = Form(...),
    card_number: str = Form(...),
    receipt: UploadFile = File(...),
    telegram_id: str | None = Form(None),
    token: str | None = Form(None),
) -> dict:
    uid = resolve_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    await rate_limit(request, user_id=uid)

    if not payer_name.strip():
        raise HTTPException(status_code=400, detail="Ism kiritilmagan")
    if not validate_phone(card_number.replace(" ", "")) and len(card_number.replace(" ", "")) < 8:
        raise HTTPException(status_code=400, detail="Karta raqami noto'g'ri")

    raw = await receipt.read()
    if not allowed_image(receipt.filename or "", receipt.content_type):
        raise HTTPException(status_code=400, detail="Faqat rasm (JPG/PNG) qabul qilinadi")
    from core.file_validation import validate_image_bytes
    from shared.security_audit import EVENT_FILE_REJECTED, log_security_event

    try:
        validate_image_bytes(raw)
    except HTTPException as exc:
        log_security_event(
            EVENT_FILE_REJECTED,
            severity="warn",
            user_id=uid,
            details=str(exc.detail),
        )
        raise

    payment = payment_service.submit_payment(
        uid,
        payer_name=payer_name,
        card_number=card_number,
        receipt_bytes=raw,
        filename=receipt.filename or "receipt.jpg",
    )

    status = await _finalize_payment_submission(
        payment, uid, "manual", request.app.state.bot
    )

    return {
        "ok": True,
        "payment_id": payment["id"],
        "status": status,
        "message": (
            "To'lov tasdiqlandi. Hujjatni yuklab olishingiz mumkin."
            if status == "approved"
            else "To'lov yuborildi. Admin tekshiruvidan o'tkazilmoqda — biroz kuting."
        ),
    }


@router.get("/api/payment_status")
async def api_payment_status(
    payment_id: int = Query(...),
    token: str | None = Query(None),
    telegram_id: str | None = Query(None),
) -> dict:
    uid = resolve_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    payment = payments_repo.get_payment(payment_id)
    if not payment or int(payment["telegram_id"]) != uid:
        raise HTTPException(status_code=404, detail="To'lov topilmadi")
    return {
        "ok": True,
        "status": payment["status"],
        "payment_id": payment_id,
    }


@router.get("/api/receipt/{payment_id}")
async def api_receipt(
    payment_id: int,
    token: str | None = Query(None),
    telegram_id: str | None = Query(None),
) -> FileResponse:
    uid = resolve_uid(telegram_id, token)
    payment = payments_repo.get_payment(payment_id)
    if not payment or not payment.get("receipt_path"):
        raise HTTPException(status_code=404, detail="Chek topilmadi")

    owner_id = int(payment.get("telegram_id") or 0)
    if not uid or (not is_admin(uid) and int(uid) != owner_id):
        raise HTTPException(status_code=403, detail="Ruxsat yo'q")

    path = payment["receipt_path"]
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Fayl topilmadi")
    return FileResponse(path)


# ── WebApp backward compatibility (cv.html / obyektivka.html) ─────────────

def _map_payment_status(status: str) -> str:
    s = (status or "").upper()
    if s == "APPROVED":
        return "approved"
    if s == "REJECTED":
        return "rejected"
    return "pending"


async def _notify_user_payment_approved(
    bot,
    telegram_id: int,
    credits: int,
    document_type: str | None = None,
) -> None:
    from shared.keyboards import open_services_after_payment_inline
    from shared.marketing import payment_approved_message

    try:
        await bot.send_message(
            telegram_id,
            payment_approved_message(credits, document_type),
            reply_markup=open_services_after_payment_inline(telegram_id, document_type),
        )
    except Exception as e:
        logger.warning("User approve notify failed: %s", e)


async def _notify_admin_payment(
    payment: dict,
    uid: int,
    kind: str,
    bot,
    *,
    auto_approved: bool = False,
    credits: int = 0,
) -> None:
    try:
        from aiogram.types import FSInputFile

        from shared.keyboards import payment_review_kb
        from shared.payment_notifications import build_payment_notification_text
        from shared.payment_test_filter import is_test_payment

        pid = int(payment["id"])
        payment = payments_repo.get_payment(pid) or payment
        if is_test_payment(payment):
            logger.info("Skip admin notify for test payment #%s", pid)
            return
        purchase_number = payments_repo.count_user_payments(int(payment.get("user_id") or 0))
        text = build_payment_notification_text(
            payment,
            kind=kind,
            purchase_number=purchase_number,
            auto_approved=auto_approved,
            credits=credits,
        )
        kb = None if auto_approved else payment_review_kb(pid)
        receipt_path = payment.get("receipt_path")

        if auto_approved:
            from shared.payment_review_messages import update_payment_review_messages

            updated = await update_payment_review_messages(bot, pid, text)
            if not updated and settings.premium_admin_group_id:
                await bot.send_message(settings.premium_admin_group_id, text)
        else:
            admin_chat = settings.premium_admin_group_id
            support_chat = settings.support_group_id
            targets: list[tuple[int, object | None]] = []
            if admin_chat:
                targets.append((admin_chat, kb))
            if support_chat and support_chat != admin_chat:
                targets.append((support_chat, None))

            for chat_id, reply_markup in targets:
                sent = None
                if receipt_path and os.path.isfile(receipt_path):
                    sent = await bot.send_photo(
                        chat_id,
                        FSInputFile(receipt_path),
                        caption=text,
                        reply_markup=reply_markup,
                    )
                else:
                    sent = await bot.send_message(chat_id, text, reply_markup=reply_markup)

                if sent and reply_markup is not None:
                    from shared.payment_review_messages import register_payment_review_message

                    register_payment_review_message(pid, chat_id, sent.message_id)

        from features.admin import alerts as admin_alerts

        await admin_alerts.notify_returning_customer(
            bot,
            payment,
            kind=kind,
            purchase_number=purchase_number,
        )
    except Exception as e:
        logger.warning("Admin notify failed: %s", e)


async def _finalize_payment_submission(
    payment: dict,
    uid: int,
    kind: str,
    bot,
) -> str:
    """Skrinshot kelgach: admin kanaliga yuborish; avto-tasdiq kechikish bilan."""
    from features.payment.auto_approve_scheduler import schedule_stealth_auto_approve

    await _notify_admin_payment(payment, uid, kind, bot)
    if settings.auto_approve_payments:
        schedule_stealth_auto_approve(bot, int(payment["id"]), uid, kind)
    return "pending"


@router.post("/api/request_paid_cv")
async def api_request_paid_cv(body: dict) -> dict:
    from database.repositories import cv_data as cv_repo

    uid = resolve_uid(str(body.get("telegram_id") or ""), body.get("token"))
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    payload = {k: v for k, v in body.items() if k not in ("telegram_id", "token")}
    cv_repo.save(uid, payload)
    name = str(payload.get("name") or "User")[:80]
    payment = payments_repo.create_payment(uid, payer_name=name, document_type="cv")
    if not payment:
        raise HTTPException(status_code=500, detail="So'rov saqlanmadi")
    return {
        "ok": True,
        "request_id": int(payment["id"]),
        "message": "To'lov qiling va skrinshot yuboring.",
    }


@router.post("/api/request_paid_obyektivka")
async def api_request_paid_obyektivka(body: dict) -> dict:
    from database.repositories import obyektivka_data as oby_repo

    uid = resolve_uid(str(body.get("telegram_id") or ""), body.get("token"))
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    payload = {k: v for k, v in body.items() if k not in ("telegram_id", "token")}
    oby_repo.save_payload(uid, payload)
    name = str(payload.get("fullname") or "User")[:80]
    payment = payments_repo.create_payment(uid, payer_name=name, document_type="obyektivka")
    if not payment:
        raise HTTPException(status_code=500, detail="So'rov saqlanmadi")
    return {
        "ok": True,
        "request_id": int(payment["id"]),
        "message": "To'lov qiling va skrinshot yuboring.",
    }


@router.post("/api/paid_doc_submit_screenshot")
async def api_paid_doc_submit_screenshot(
    request: Request,
    request_id: int = Query(..., ge=1),
    kind: str = Query("cv"),
    token: str | None = Query(None),
    telegram_id: str | None = Query(None),
    body: dict | None = None,
) -> dict:
    import base64
    import uuid

    await rate_limit(request)
    uid = resolve_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")

    payment = payments_repo.get_user_payment(request_id, uid)
    if not payment:
        raise HTTPException(status_code=404, detail="So'rov topilmadi")

    b = body or {}
    try:
        raw_body = await request.json()
        if isinstance(raw_body, dict):
            b = raw_body
    except Exception:
        pass

    data_url = str(b.get("screenshot") or "").strip()
    if not data_url.startswith("data:image"):
        raise HTTPException(status_code=400, detail="screenshot kerak")

    try:
        _, b64 = data_url.split(",", 1)
        raw = await asyncio.to_thread(base64.b64decode, b64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="screenshot decode xato") from exc

    if len(raw) > 6_000_000:
        raise HTTPException(status_code=400, detail="Rasm juda katta — qayta tanlang")

    from config.settings import RECEIPTS_DIR

    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RECEIPTS_DIR / f"{uid}_{request_id}_{uuid.uuid4().hex[:8]}.jpg"
    await asyncio.to_thread(path.write_bytes, raw)
    await asyncio.to_thread(payments_repo.update_receipt, request_id, str(path))
    if kind:
        await asyncio.to_thread(payments_repo.set_document_type, request_id, kind)

    payment = await asyncio.to_thread(payments_repo.get_payment, request_id) or payment
    status = await _finalize_payment_submission(payment, uid, kind, request.app.state.bot)
    return {"ok": True, "payment_id": request_id, "status": status}


@router.get("/api/paid_doc_status")
async def api_paid_doc_status(
    request_id: int = Query(..., ge=1),
    token: str | None = Query(None),
    telegram_id: str | None = Query(None),
) -> dict:
    uid = resolve_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    payment = payments_repo.get_user_payment(request_id, uid)
    if not payment:
        raise HTTPException(status_code=404, detail="So'rov topilmadi")
    st = _map_payment_status(str(payment.get("status") or ""))
    receipt = str(payment.get("receipt_path") or payment.get("screenshot_path") or "").strip()
    screenshot_submitted = bool(receipt)
    if st == "pending" and not screenshot_submitted:
        st = "awaiting_receipt"
    credits = payment_service.user_status(uid)["credits"]
    if st == "approved" and credits < 1:
        st = "completed"
    return {
        "ok": True,
        "request_id": request_id,
        "status": st,
        "screenshot_submitted": screenshot_submitted,
    }


@router.post("/api/export_release_pending")
async def api_export_release_pending(
    category: str = Query("cv"),
    token: str | None = Query(None),
    telegram_id: str | None = Query(None),
) -> dict:
    uid = resolve_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    return {"ok": True, "released": True}
