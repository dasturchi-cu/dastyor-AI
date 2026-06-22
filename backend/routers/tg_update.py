"""Telegram webhook ingress — Aiogram 3."""
from __future__ import annotations

import logging

from aiogram.types import Update
from fastapi import APIRouter, Request, Response

logger = logging.getLogger(__name__)
router = APIRouter(tags=["telegram-webhook"])


@router.post("/webhook")
async def webhook(request: Request) -> Response:
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
