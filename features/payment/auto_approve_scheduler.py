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
            from features.payment.router import _notify_user_payment_approved
            from shared.payment_notifications import build_payment_notification_text
            from shared.payment_review_messages import update_payment_review_messages

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
            purchase_number = payments_repo.count_user_payments(int(result.get("user_id") or 0))
            resolved_text = build_payment_notification_text(
                result,
                kind=kind,
                purchase_number=purchase_number,
                auto_approved=True,
                credits=credits,
            )
            updated = await update_payment_review_messages(bot, payment_id, resolved_text)
            if not updated:
                from features.payment.router import _notify_admin_payment

                await _notify_admin_payment(
                    result, uid, kind, bot, auto_approved=True, credits=credits
                )
            else:
                from features.admin import alerts as admin_alerts

                await admin_alerts.notify_returning_customer(
                    bot,
                    result,
                    kind=kind,
                    purchase_number=purchase_number,
                )
            await _notify_user_payment_approved(bot, tid, credits, result.get("document_type"))
            ref_info = result.get("referral_info")
            if ref_info:
                from shared.referral import notify_referrer

                await notify_referrer(bot, ref_info, event="payment")
            logger.info("Stealth auto-approve done #%s after %ss", payment_id, delay)
        except asyncio.CancelledError:
            logger.debug("Stealth auto-approve cancelled #%s", payment_id)
        except Exception as exc:
            logger.exception("Stealth auto-approve error #%s: %s", payment_id, exc)
        finally:
            _tasks.pop(int(payment_id), None)

    _tasks[int(payment_id)] = asyncio.create_task(_run())
    logger.info("Stealth auto-approve scheduled #%s in %ss", payment_id, delay)
