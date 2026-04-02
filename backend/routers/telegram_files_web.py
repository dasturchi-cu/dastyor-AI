"""Upload delivery to Telegram + premium receipt from WebApp."""
from __future__ import annotations

import html as html_lib
import io
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from telegram import InputFile, InlineKeyboardButton, InlineKeyboardMarkup

from backend.dependencies import get_ptb_application
from backend.services.upload_io import EmptyUploadError, UploadTooLargeError, read_upload_limited
from backend.services.user_resolve import resolve_telegram_uid, safe_filename_part
from backend.web_constants import PREMIUM_ADMIN_GROUP_ID

logger = logging.getLogger(__name__)

router = APIRouter(tags=["web-telegram-files"])


@router.post("/api/upload_to_telegram")
async def api_upload_to_telegram(
    file: UploadFile = File(...),
    telegram_id: str = Form(None),
    token: str = Form(None),
    caption: str = Form(""),
    ptb=Depends(get_ptb_application),
):
    uid = resolve_telegram_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        content = await read_upload_limited(file)
    except EmptyUploadError:
        return {"ok": False, "error": "Empty file"}
    except UploadTooLargeError as e:
        return {"ok": False, "error": str(e)}

    logger.info("Sending frontend-generated file %s to UID %s", file.filename, uid)

    buf = io.BytesIO(content)
    buf.name = file.filename or "file.bin"

    try:
        if (file.filename or "").lower().endswith(".docx"):
            from bot.utils.delivery import send_docx_with_confirmation

            ok = await send_docx_with_confirmation(
                ptb.bot,
                int(uid),
                buf,
                filename=file.filename,
                caption=caption or "✅ Faylingiz tayyorlandi!",
            )
            if not ok:
                return {"ok": False, "error": "Word fayl yuborilmadi"}
        else:
            await ptb.bot.send_document(
                chat_id=int(uid),
                document=InputFile(buf, filename=file.filename or "file.bin"),
                caption=caption or "✅ Faylingiz tayyorlandi!",
            )
        return {"ok": True}
    except Exception as e:
        logger.error("Error sending file via /api/upload_to_telegram: %s", e, exc_info=True)
        return {"ok": False, "error": str(e)}


@router.post("/api/premium_receipt")
async def api_premium_receipt(
    file: UploadFile = File(...),
    plan: str = Form("premium"),
    telegram_id: str = Form(None),
    token: str = Form(None),
    ptb=Depends(get_ptb_application),
):
    uid = resolve_telegram_uid(telegram_id, token)
    if not uid:
        raise HTTPException(
            status_code=401,
            detail="Kirish aniqlanmadi. WebAppni yoping va botdan qayta oching (token yoki telegram_id).",
        )

    safe_plan = (plan or "premium").strip().lower()
    if safe_plan not in ("standard", "premium"):
        safe_plan = "premium"

    filename = safe_filename_part(file.filename or "receipt.jpg", "receipt.jpg")
    try:
        content = await read_upload_limited(file)
    except EmptyUploadError:
        raise HTTPException(status_code=400, detail="Fayl bo‘sh. Boshqa rasm tanlang.")
    except UploadTooLargeError:
        raise HTTPException(
            status_code=413,
            detail="Rasm juda katta. Skrinshotni qisqartiring yoki kichikroq fayl yuboring.",
        )

    first_name = ""
    username = ""
    if token:
        try:
            from bot.services.session_service import resolve_session

            sess = resolve_session(token) or {}
            first_name = sess.get("first_name") or ""
            username = sess.get("username") or ""
        except Exception:
            pass

    request_id = None
    payment_id = None
    try:
        from bot.services.supabase_db import db_create_payment, has_db

        if has_db():
            amount = 10000 if safe_plan == "standard" else 30000
            payment_id = db_create_payment(
                user_id=int(uid),
                plan_type=safe_plan,
                amount=amount,
                screenshot_url=None,
                metadata={"source": "webapp"},
            )
    except Exception:
        payment_id = None

    if payment_id:
        request_id = payment_id
    else:
        from bot.services.premium_purchase_db import create_payment_request

        request_id = create_payment_request(
            user_id=int(uid),
            plan_type=safe_plan,
            username=username or "",
            first_name=first_name or "",
        )

    uname = f"@{username}" if username else "yo'q"
    display_name = first_name or "Noma'lum"
    plan_title = "Standart" if safe_plan == "standard" else "Premium"
    cap = (
        "💰 <b>Yangi premium to'lov (WebApp)</b>\n\n"
        f"So'rov ID: <code>{request_id}</code>\n"
        f"Ism: <b>{html_lib.escape(display_name)}</b>\n"
        f"Username: {html_lib.escape(uname)}\n"
        f"User ID: <code>{uid}</code>\n"
        f"Tarif: <b>{plan_title}</b>"
    )
    review_kb = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"prempay_approve_{request_id}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"prempay_reject_{request_id}"),
        ]]
    )

    try:
        buf = io.BytesIO(content)
        buf.name = filename
        ext = (filename.rsplit(".", 1)[-1].lower() if "." in filename else "")

        if ext in ("jpg", "jpeg", "png", "webp", "bmp", "gif"):
            await ptb.bot.send_photo(
                chat_id=PREMIUM_ADMIN_GROUP_ID,
                photo=InputFile(buf, filename=filename),
                caption=cap,
                parse_mode="HTML",
                reply_markup=review_kb,
            )
        else:
            await ptb.bot.send_document(
                chat_id=PREMIUM_ADMIN_GROUP_ID,
                document=InputFile(buf, filename=filename),
                caption=cap,
                parse_mode="HTML",
                reply_markup=review_kb,
            )

        await ptb.bot.send_message(
            chat_id=int(uid),
            text="✅ Chek qabul qilindi va adminga yuborildi. Tasdiqdan so'ng premium yoqiladi.",
        )
        return {"ok": True}
    except Exception as e:
        logger.error("/api/premium_receipt error: %s", e, exc_info=True)
        msg = str(e).strip()[:400]
        if "chat not found" in msg.lower() or "peer_id_invalid" in msg.lower():
            detail = (
                "Admin guruh/chat topilmadi (bot guruhga qo‘shilmagan yoki PREMIUM_ADMIN_GROUP_ID noto‘g‘ri). "
                "Texnik xizmatga murojaat qiling."
            )
        elif "bot was blocked" in msg.lower() or "forbidden" in msg.lower():
            detail = (
                "Bot foydalanuvchi yoki guruh bilan xabar almasha olmayapti. "
                "Botni guruhga qo‘shing va xabar yuborish huquqini tekshiring."
            )
        elif "wrong file" in msg.lower() or "can't use file" in msg.lower():
            detail = "Rasm fayli yaroqsiz. Boshqa skrinshot yuboring (JPG/PNG)."
        else:
            detail = (
                "Chek yuborishda texnik xatolik. Internetni tekshirib keyinroq qayta urinib ko‘ring. "
                f"(tafsilot: {msg[:180]})" if msg else "Chek yuborishda texnik xatolik."
            )
        raise HTTPException(status_code=502, detail=detail) from e
