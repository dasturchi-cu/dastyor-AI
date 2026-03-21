"""Telegram Bot API webhook ingress."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request, Response
from telegram import Update

logger = logging.getLogger(__name__)

router = APIRouter(tags=["telegram-webhook"])


@router.post("/webhook")
async def webhook(request: Request):
    try:
        logger.info("Telegram webhook hit path=%s method=%s", request.url.path, request.method)
        ptb = request.app.state.ptb_application
        data = await request.json()
        update = Update.de_json(data, ptb.bot)
        await ptb.process_update(update)
        return Response(status_code=200)
    except Exception as e:
        logger.error("Error processing update: %s", e, exc_info=True)
        return Response(status_code=500)


@router.post("/")
async def webhook_root(request: Request):
    """Some providers POST updates to `/` when webhook URL has no path."""
    return await webhook(request)
