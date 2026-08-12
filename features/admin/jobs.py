"""Background admin jobs — daily report at 21:00, pending payment reminders."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot

from config.settings import settings
from features.admin import alerts as admin_alerts

logger = logging.getLogger(__name__)

_task: asyncio.Task | None = None
_stop = asyncio.Event()


def _tz() -> ZoneInfo:
    try:
        return ZoneInfo(settings.admin_report_timezone or "Asia/Tashkent")
    except Exception:
        return ZoneInfo("Asia/Tashkent")


async def _jobs_loop(bot: Bot) -> None:
    last_reminder_minute: str | None = None
    while not _stop.is_set():
        try:
            now = datetime.now(_tz())
            report_hour = settings.admin_report_hour
            today = now.date().isoformat()

            if now.hour == report_hour:
                from database.repositories import settings as settings_repo

                if settings_repo.get(admin_alerts._DAILY_REPORT_KEY) != today:
                    await admin_alerts.send_daily_report(bot)

            # Check stale pending payments every 15 minutes
            minute_key = f"{now.date().isoformat()}:{now.hour}:{now.minute // 15}"
            if minute_key != last_reminder_minute:
                last_reminder_minute = minute_key
                count = await admin_alerts.check_pending_payment_reminders(bot)
                if count:
                    logger.info("Sent %s pending payment reminder(s)", count)
        except Exception as exc:
            logger.exception("Admin jobs loop error: %s", exc)

        try:
            await asyncio.wait_for(_stop.wait(), timeout=60.0)
        except asyncio.TimeoutError:
            pass


def start_admin_jobs(bot: Bot) -> None:
    global _task
    if _task and not _task.done():
        return
    _stop.clear()
    _task = asyncio.create_task(_jobs_loop(bot), name="admin_jobs")
    logger.info(
        "Admin jobs started (daily report %s:00 %s)",
        settings.admin_report_hour,
        settings.admin_report_timezone,
    )


async def stop_admin_jobs() -> None:
    global _task
    _stop.set()
    if _task:
        try:
            await asyncio.wait_for(_task, timeout=5.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            _task.cancel()
        _task = None
