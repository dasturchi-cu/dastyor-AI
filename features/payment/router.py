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
from features.payment import service as payment_service
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

    user = users_repo.get_by_telegram_id(uid) or users_repo.upsert_user(uid)
    session = get_session_by_telegram_id(uid) or {}
    return {
        "ok": True,
        "telegram_id": uid,
        "first_name": session.get("first_name", user.get("first_name", "")),
        "username": session.get("username", user.get("username", "")),
        "credits": int(user.get("credits") or 0),
        "single_doc_price_uzs": settings.single_doc_price_uzs,
        "has_access": int(user.get("credits") or 0) > 0,
        "credit_note": "1 kredit = 1 ta hujjat (CV yoki Obyektivka)",
    }


@router.post("/api/auth")
async def api_auth(req: AuthRequest) -> dict:
    from shared.session_service import create_session
    from database.repositories import users as users_repo

    body = req
    init_data = (body.init_data or "").strip()

    if not settings.allow_insecure_auth:
        if not init_data:
            raise HTTPException(status_code=401, detail="init_data talab qilinadi")
        validated = validate_init_data(
            init_data,
            settings.bot_token,
            max_age_seconds=settings.init_data_max_age_seconds,
        )
        if not validated:
            raise HTTPException(status_code=401, detail="init_data noto'g'ri yoki muddati o'tgan")
        verified_id = extract_telegram_user_id(validated)
        if not verified_id or int(verified_id) != int(body.telegram_id):
            raise HTTPException(status_code=401, detail="Foydalanuvchi tasdiqlanmadi")

    users_repo.upsert_user(
        body.telegram_id,
        username=body.username,
        first_name=body.first_name,
    )
    token = create_session(
        telegram_id=body.telegram_id,
        first_name=body.first_name,
        username=body.username,
        photo_url=body.photo_url,
    )
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
    await rate_limit(request)
    uid = resolve_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")

    if not payer_name.strip():
        raise HTTPException(status_code=400, detail="Ism kiritilmagan")
    if not validate_phone(card_number.replace(" ", "")) and len(card_number.replace(" ", "")) < 8:
        raise HTTPException(status_code=400, detail="Karta raqami noto'g'ri")

    raw = await receipt.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Chek rasmi bo'sh")
    if not allowed_image(receipt.filename or "", receipt.content_type):
        raise HTTPException(status_code=400, detail="Faqat rasm (JPG/PNG) qabul qilinadi")

    payment = payment_service.submit_payment(
        uid,
        payer_name=payer_name,
        card_number=card_number,
        receipt_bytes=raw,
        filename=receipt.filename or "receipt.jpg",
    )

    asyncio.create_task(
        _notify_admin_payment(payment, uid, "manual", request.app.state.bot)
    )

    return {
        "ok": True,
        "payment_id": payment["id"],
        "message": "To'lov yuborildi. Admin tasdiqlashini kuting.",
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


async def _notify_admin_payment(payment: dict, uid: int, kind: str, bot) -> None:
    try:
        from aiogram.types import FSInputFile
        from shared.keyboards import payment_review_kb

        pid = int(payment["id"])
        admin_chat = settings.premium_admin_group_id
        payer = str(payment.get("payer_name") or uid)
        if kind == "manual":
            text = (
                f"💳 <b>Yangi to'lov #{pid}</b>\n"
                f"👤 {payer}\n"
                f"🆔 <code>{uid}</code>\n"
                f"💳 <code>{payment.get('card_number') or '-'}</code>"
            )
        else:
            text = (
                f"💰 <b>Yangi to'lov</b>\n"
                f"Payment ID: <code>{pid}</code>\n"
                f"User: <code>{uid}</code>\n"
                f"Xizmat: <b>{kind}</b>\n"
                f"Narx: <b>{settings.single_doc_price_uzs:,} so'm</b>"
            )
        kb = payment_review_kb(pid)
        receipt_path = payment.get("receipt_path")
        if receipt_path and os.path.isfile(receipt_path):
            await bot.send_photo(
                admin_chat,
                FSInputFile(receipt_path),
                caption=text,
                reply_markup=kb,
            )
        else:
            await bot.send_message(admin_chat, text, reply_markup=kb)
    except Exception as e:
        logger.warning("Admin notify failed: %s", e)


@router.post("/api/request_paid_cv")
async def api_request_paid_cv(body: dict) -> dict:
    from database.repositories import cv_data as cv_repo

    uid = resolve_uid(str(body.get("telegram_id") or ""), body.get("token"))
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    payload = {k: v for k, v in body.items() if k not in ("telegram_id", "token")}
    cv_repo.save(uid, payload)
    name = str(payload.get("name") or "User")[:80]
    payment = payments_repo.create_payment(uid, payer_name=name)
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
    payment = payments_repo.create_payment(uid, payer_name=name)
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

    payment = await asyncio.to_thread(payments_repo.get_payment, request_id) or payment
    asyncio.create_task(_notify_admin_payment(payment, uid, kind, request.app.state.bot))
    return {"ok": True, "payment_id": request_id, "status": "queued_to_admin"}


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
    credits = payment_service.user_status(uid)["credits"]
    if st == "approved" and credits < 1:
        st = "completed"
    return {"ok": True, "request_id": request_id, "status": st}


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
