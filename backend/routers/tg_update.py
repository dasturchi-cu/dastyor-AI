"""Telegram webhook ingress — Aiogram 3."""
from __future__ import annotations

import hmac
import logging

from aiogram.types import Update
from fastapi import APIRouter, Request, Response

from config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["telegram-webhook"])


def _verify_webhook_secret(request: Request) -> bool:
    secret = (getattr(request.app.state, "webhook_secret", None) or settings.webhook_secret or "").strip()
    if not secret:
        return True
    got = (request.headers.get("X-Telegram-Bot-Api-Secret-Token") or "").strip()
    return bool(got) and hmac.compare_digest(got, secret)


@router.post("/webhook")
async def webhook(request: Request) -> Response:
    if not _verify_webhook_secret(request):
        from core.security import client_ip
        from shared.security_audit import EVENT_WEBHOOK_REJECTED, log_security_event

        log_security_event(EVENT_WEBHOOK_REJECTED, severity="critical", ip=client_ip(request))
        logger.warning("Webhook rejected: invalid secret token")
        return Response(status_code=403)

    try:
        bot = request.app.state.bot
        dp = request.app.state.dp
        data = await request.json()
        update = Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot, update)
        return Response(status_code=200)
    except Exception as e:
        logger.error("Webhook error: %s", e, exc_info=True)
        return Response(status_code=500)


@router.post("/")
async def webhook_root(request: Request) -> Response:
    return await webhook(request)
