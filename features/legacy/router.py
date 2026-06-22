"""Legacy WebApp API routes (translit, translate, notify, stats)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from backend.schemas.webapp import NotifyRequest, TranslateRequest, TranslitRequest
from backend.services.auto_script import auto_cyrillic_latin
from features.ai.gemini_client import translate_text
from core.security import rate_limit
from database.repositories import users as users_repo
from shared.auth import resolve_uid

logger = logging.getLogger(__name__)
router = APIRouter(tags=["legacy"])


@router.post("/api/translit")
async def api_translit(body: TranslitRequest, request: Request) -> dict:
    await rate_limit(request)
    uid = resolve_uid(
        str(body.telegram_id) if body.telegram_id else None,
        body.token,
    )
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    result = auto_cyrillic_latin(body.text)
    return {
        "ok": True,
        "result": result.result,
        "direction": result.direction,
    }


@router.post("/api/translate")
async def api_translate(body: TranslateRequest, request: Request) -> dict:
    await rate_limit(request)
    uid = resolve_uid(
        str(body.telegram_id) if body.telegram_id else None,
        body.token,
    )
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    if not (body.text or "").strip():
        raise HTTPException(status_code=400, detail="Matn bo'sh")
    translated = await translate_text(body.text, direction=body.direction or "uz_en")
    return {"ok": True, "result": translated}


@router.post("/api/notify")
async def api_notify(body: NotifyRequest, request: Request) -> dict:
    await rate_limit(request)
    uid = resolve_uid(str(body.telegram_id), body.token)
    if not uid or int(uid) != int(body.telegram_id):
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    bot = getattr(request.app.state, "bot", None)
    if not bot:
        raise HTTPException(status_code=503, detail="Bot mavjud emas")
    try:
        await bot.send_message(int(uid), str(body.message)[:4000])
        return {"ok": True}
    except Exception as e:
        logger.warning("notify failed: %s", e)
        raise HTTPException(status_code=500, detail="Xabar yuborib bo'lmadi") from e


@router.get("/api/stats")
async def api_stats(
    request: Request,
    telegram_id: str | None = None,
    token: str | None = None,
) -> dict:
    uid = resolve_uid(telegram_id, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Foydalanuvchi aniqlanmadi")
    user = users_repo.get_by_telegram_id(uid) or users_repo.upsert_user(uid)
    return {
        "ok": True,
        "telegram_id": uid,
        "credits": int(user.get("credits") or 0),
        "users_total": users_repo.count_users(),
    }
