"""Admin scheduled alerts — daily report, pending reminders, returning customers."""
from __future__ import annotations

import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.types import FSInputFile

from config.settings import settings
from database.repositories import admin_stats as stats_repo
from database.repositories import payments as payments_repo
from database.repositories import settings as settings_repo
from shared.keyboards import payment_review_kb
from shared.payment_notifications import (
    build_daily_admin_report,
    build_pending_payment_reminder,
    build_returning_customer_alert,
)

logger = logging.getLogger(__name__)

_DAILY_REPORT_KEY = "admin_daily_report_date"


def _admin_chat_ids() -> list[int]:
    chats: list[int] = []
    if settings.premium_admin_group_id:
        chats.append(settings.premium_admin_group_id)
    return chats


async def _send_admin(bot: Bot, text: str, *, reply_markup=None) -> None:
    for chat_id in _admin_chat_ids():
        try:
            await bot.send_message(chat_id, text, reply_markup=reply_markup)
        except Exception as exc:
            logger.warning("Admin alert to %s failed: %s", chat_id, exc)


async def send_daily_report(bot: Bot) -> bool:
    """Send today's report. Returns True if sent."""
    tz_name = settings.admin_report_timezone or "Asia/Tashkent"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("Asia/Tashkent")
    now = datetime.now(tz)
    today = now.date().isoformat()
    if settings_repo.get(_DAILY_REPORT_KEY) == today:
        return False

    stats = stats_repo.daily_report_stats()
    text = build_daily_admin_report(stats, report_date=today)
    await _send_admin(bot, text)
    settings_repo.set_value(_DAILY_REPORT_KEY, today)
    logger.info("Daily admin report sent for %s", today)
    return True


async def check_pending_payment_reminders(bot: Bot) -> int:
    """Notify admin about stale pending payments. Returns count sent."""
    hours = settings.pending_payment_reminder_hours
    stale = payments_repo.list_stale_pending(hours=hours, limit=20)
    sent = 0
    for payment in stale:
        pid = int(payment["id"])
        text = build_pending_payment_reminder(payment, hours_pending=hours)
        kb = payment_review_kb(pid)
        receipt = payment.get("receipt_path")
        for chat_id in _admin_chat_ids():
            try:
                if receipt and os.path.isfile(receipt):
                    await bot.send_photo(
                        chat_id,
                        FSInputFile(receipt),
                        caption=text,
                        reply_markup=kb,
                    )
                else:
                    await bot.send_message(chat_id, text, reply_markup=kb)
            except Exception as exc:
                logger.warning("Pending reminder #%s failed: %s", pid, exc)
                continue
        payments_repo.mark_pending_reminder_sent(pid)
        sent += 1
    return sent


async def notify_returning_customer(
    bot: Bot,
    payment: dict,
    *,
    kind: str,
    purchase_number: int,
) -> None:
    user_id = int(payment.get("user_id") or 0)
    pid = int(payment.get("id") or 0)
    if not user_id:
        return
    previous_approved = payments_repo.count_user_approved_payments(
        user_id,
        exclude_payment_id=pid,
    )
    if previous_approved < 1:
        return
    text = build_returning_customer_alert(
        payment,
        kind=kind,
        purchase_number=purchase_number,
        previous_approved=previous_approved,
    )
    await _send_admin(bot, text)
