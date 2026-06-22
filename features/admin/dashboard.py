"""Real-time admin dashboard with auto-refresh."""
from __future__ import annotations

import asyncio
import html
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from config.settings import settings
from database.repositories import admin_stats as stats_repo
from features.admin.formatters import build_dashboard_text as _build_dashboard_text
from shared.payment_notifications import format_username

logger = logging.getLogger(__name__)

_sessions: dict[int, "DashboardSession"] = {}


@dataclass
class DashboardSession:
    admin_id: int
    chat_id: int
    message_id: int
    task: asyncio.Task | None = field(default=None, repr=False)


def _tz_now() -> datetime:
    try:
        tz = ZoneInfo(settings.admin_report_timezone or "Asia/Tashkent")
    except Exception:
        tz = ZoneInfo("Asia/Tashkent")
    return datetime.now(tz)


def _feed_line(event: dict[str, Any]) -> str:
    name = html.escape((event.get("actor_name") or "Foydalanuvchi").strip())
    et = str(event.get("event_type") or "").lower()
    labels = {
        "register": f"{name} ro'yxatdan o'tdi",
        "cv": f"{name} CV yaratdi",
        "obyektivka": f"{name} Obyektivka yaratdi",
        "payment": f"{name} to'lov qildi",
        "download": f"{name} hujjat yukladi",
    }
    return labels.get(et, f"{name} — {html.escape(str(event.get('detail') or et))}")


def build_dashboard_text(snapshot: dict[str, Any], *, updated_at: str | None = None) -> str:
    ts = updated_at or _tz_now().strftime("%H:%M:%S")
    return _build_dashboard_text(snapshot, updated_at=ts)


async def _refresh_loop(bot: Bot, session: DashboardSession) -> None:
    interval = max(5, min(10, settings.admin_dashboard_refresh_sec))
    while session.admin_id in _sessions:
        try:
            snapshot = await asyncio.to_thread(stats_repo.dashboard_snapshot)
            text = build_dashboard_text(snapshot)
            await bot.edit_message_text(
                text,
                chat_id=session.chat_id,
                message_id=session.message_id,
            )
        except TelegramBadRequest as exc:
            if "message is not modified" not in str(exc).lower():
                logger.debug("Dashboard edit stopped: %s", exc)
                break
        except Exception as exc:
            logger.warning("Dashboard refresh error: %s", exc)
            break
        await asyncio.sleep(interval)


def stop_dashboard(admin_id: int) -> None:
    session = _sessions.pop(int(admin_id), None)
    if session and session.task and not session.task.done():
        session.task.cancel()


async def start_dashboard(bot: Bot, *, admin_id: int, chat_id: int) -> int:
    stop_dashboard(admin_id)
    snapshot = await asyncio.to_thread(stats_repo.dashboard_snapshot)
    text = build_dashboard_text(snapshot)
    msg = await bot.send_message(chat_id, text)
    session = DashboardSession(admin_id=admin_id, chat_id=chat_id, message_id=msg.message_id)
    session.task = asyncio.create_task(_refresh_loop(bot, session), name=f"dash_{admin_id}")
    _sessions[admin_id] = session
    return msg.message_id

