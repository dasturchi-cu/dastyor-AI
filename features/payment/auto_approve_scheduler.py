"""Kechiktirib avtomatik tasdiqlash — foydalanuvchi admin tekshirayotgandek ko'radi."""
from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

from config.settings import settings

logger = logging.getLogger(__name__)

_tasks: dict[int, asyncio.Task[Any]] = {}


def cancel_auto_approve(payment_id: int) -> bool:
    task = _tasks.pop(int(payment_id), None)
    if task and not task.done():
        task.cancel()
        return True
    return False


def is_auto_approve_scheduled(payment_id: int) -> bool:
    task = _tasks.get(int(payment_id))
    return bool(task and not task.done())


def schedule_stealth_auto_approve(
    bot,
    payment_id: int,
    uid: int,
    kind: str,
) -> None:
    """Admin ko'rinishidagi kechikishdan keyin avtomatik tasdiqlash."""
    if not settings.auto_approve_payments:
        return

    cancel_auto_approve(payment_id)

    lo = max(8, int(settings.auto_approve_delay_min_sec))
    hi = max(lo, int(settings.auto_approve_delay_max_sec))
    delay = random.randint(lo, hi)

    async def _run() -> None:
        try:
            await asyncio.sleep(delay)
            from database.repositories import payments as payments_repo
            from database.repositories import users as users_repo
            from features.payment import service as payment_service
            from features.payment.router import (
                _notify_admin_payment,
                _notify_user_payment_approved,
            )

            payment = payments_repo.get_payment(payment_id)
            if not payment:
                return
            if str(payment.get("status") or "").upper() != "PENDING":
                logger.info("Stealth auto-approve skipped #%s — status changed", payment_id)
                return

            result = payment_service.try_auto_approve(payment_id)
            if not result:
                logger.warning("Stealth auto-approve failed #%s", payment_id)
                return

            tid = int(result["telegram_id"])
            credits = users_repo.get_credits(tid)
            await _notify_admin_payment(
                result, uid, kind, bot, auto_approved=True, credits=credits
            )
            await _notify_user_payment_approved(bot, tid, credits)
            logger.info("Stealth auto-approve done #%s after %ss", payment_id, delay)
        except asyncio.CancelledError:
            logger.debug("Stealth auto-approve cancelled #%s", payment_id)
        except Exception as exc:
            logger.exception("Stealth auto-approve error #%s: %s", payment_id, exc)
        finally:
            _tasks.pop(int(payment_id), None)

    _tasks[int(payment_id)] = asyncio.create_task(_run())
    logger.info("Stealth auto-approve scheduled #%s in %ss", payment_id, delay)
