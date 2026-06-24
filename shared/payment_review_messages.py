"""Admin to'lov xabarlarini saqlash va tasdiqlash/rad etishdan keyin yangilash."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# payment_id → [(chat_id, message_id), ...]
_refs: dict[int, list[tuple[int, int]]] = {}


def register_payment_review_message(payment_id: int, chat_id: int, message_id: int) -> None:
    pid = int(payment_id)
    refs = _refs.setdefault(pid, [])
    pair = (int(chat_id), int(message_id))
    if pair not in refs:
        refs.append(pair)


def clear_payment_review_messages(payment_id: int) -> None:
    _refs.pop(int(payment_id), None)


async def update_payment_review_messages(bot: Any, payment_id: int, text: str) -> int:
    """Tepadagi to'lov xabarini tahrirlash (tugmalarni olib tashlash)."""
    refs = _refs.pop(int(payment_id), [])
    updated = 0
    for chat_id, message_id in refs:
        if await _edit_admin_message(bot, chat_id, message_id, text):
            updated += 1
    return updated


async def _edit_admin_message(bot: Any, chat_id: int, message_id: int, text: str) -> bool:
    try:
        await bot.edit_message_caption(
            chat_id=chat_id,
            message_id=message_id,
            caption=text,
            reply_markup=None,
        )
        return True
    except Exception:
        pass
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=None,
        )
        return True
    except Exception as exc:
        logger.warning(
            "Payment review message edit failed chat=%s msg=%s: %s",
            chat_id,
            message_id,
            exc,
        )
        try:
            await bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=None,
            )
        except Exception:
            pass
    return False
