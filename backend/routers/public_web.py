"""Minimal Web APIs for CV/Obyektivka and admin notifications."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies import get_ptb_application
from backend.schemas.webapp import AuthRequest, NotifyRequest, ObjectiveRequest, SupportRequest
from backend.services.user_resolve import resolve_telegram_uid
from bot.services.ai_service import generate_objective
from bot.services.session_service import create_session, get_session_by_telegram_id
from bot.services.support_service import create_support_request
from bot.services.user_service import get_user_profile, track_user_activity

router = APIRouter(tags=["web-api"])


@router.post("/api/auth")
async def api_auth(req: AuthRequest) -> dict:
    token = create_session(
        telegram_id=req.telegram_id,
        first_name=req.first_name,
        username=req.username,
        photo_url=req.photo_url,
    )

    class _U:
        id = req.telegram_id
        first_name = req.first_name
        username = req.username

    track_user_activity(_U(), command="web_auth", chat_id=int(req.telegram_id))
    return {"ok": True, "token": token, "telegram_id": req.telegram_id}


@router.get("/api/me")
async def api_me(token: str | None = Query(None), telegram_id: str | None = Query(None)) -> dict:
    uid = resolve_telegram_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")

    profile = get_user_profile(uid) or {}
    session = get_session_by_telegram_id(uid) or {}
    return {
        "ok": True,
        "telegram_id": uid,
        "first_name": session.get("first_name", profile.get("first_name", "")),
        "username": session.get("username", profile.get("username", "")),
        "photo_url": session.get("photo_url", ""),
        "files_processed": profile.get("files_processed", 0),
        "joined_at": profile.get("joined_at", ""),
        "last_active": profile.get("last_active", ""),
    }


@router.post("/api/objective")
async def api_objective(req: ObjectiveRequest) -> dict:
    role = (req.role or "").strip()
    if not role:
        raise HTTPException(status_code=400, detail="Role bo'sh bo'lishi mumkin emas")

    text = await generate_objective(
        role=role,
        experience=req.experience,
        extra=req.extra or "",
        lang=req.lang or "uz",
    )
    if not text:
        raise HTTPException(status_code=502, detail="Objective yaratib bo'lmadi")

    return {"ok": True, "text": text}


@router.post("/api/support")
async def api_support(req: SupportRequest, ptb=Depends(get_ptb_application)) -> dict:
    uid = resolve_telegram_uid(str(req.telegram_id), req.token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")

    msg = (req.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Xabar bo'sh")

    saved = create_support_request(
        user_id=int(uid),
        username=req.username or "",
        message=msg,
        source="webapp",
    )
    admin_chat = int(os.getenv("SUPPORT_GROUP_ID", "-1003457224552"))
    await ptb.bot.send_message(
        chat_id=admin_chat,
        text=(
            "📩 <b>Yangi murojaat</b>\n\n"
            f"🎫 ID: <b>#{saved['id']}</b>\n"
            f"🆔 User: <code>{uid}</code>\n\n"
            f"💬 {msg}"
        ),
        parse_mode="HTML",
    )
    return {"ok": True, "request_id": saved["id"]}


@router.post("/api/notify")
async def api_notify(req: NotifyRequest, ptb=Depends(get_ptb_application)) -> dict:
    uid = resolve_telegram_uid(str(req.telegram_id), req.token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")

    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Xabar bo'sh")

    await ptb.bot.send_message(chat_id=int(uid), text=req.message, parse_mode="HTML")
    return {"ok": True}
