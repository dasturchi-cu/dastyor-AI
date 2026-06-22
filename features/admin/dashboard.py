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
from shared.payment_notifications import format_username, purchase_ordinal_uz

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
    revenue = int(snapshot.get("revenue_uzs") or 0)
    conv = snapshot.get("conversion_pct", 0)

    lines = [
        "<b>🛠 ADMIN DASHBOARD</b>",
        f"<i>🔄 {ts} | real-time</i>",
        "",
        "<b>🔥 JONLI TA'MINOT</b>",
    ]
    feed = snapshot.get("feed") or []
    if feed:
        for ev in feed[:6]:
            lines.append(f"• {_feed_line(ev)}")
    else:
        lines.append("<i>Hozircha faollik yo'q</i>")

    lines.extend(
        [
            "",
            "━━━━━━━━━━━━━━",
            f"👥 Onlayn: <b>{snapshot.get('online_users', 0)}</b>",
            f"📈 Bugun userlar: <b>{snapshot.get('today_users', 0)}</b>",
            f"💳 Kutilayotgan to'lovlar: <b>{snapshot.get('pending_payments', 0)}</b>",
            f"📄 CV bugun: <b>{snapshot.get('cv', 0)}</b>",
            f"📋 Obyektivka bugun: <b>{snapshot.get('obyektivka', 0)}</b>",
            f"💰 Tushum bugun: <b>{revenue:,} so'm</b>",
            f"🔥 Faol userlar: <b>{snapshot.get('active_users', 0)}</b>",
            f"😴 Nofaol userlar: <b>{snapshot.get('inactive_users', 0)}</b>",
            "",
            "<b>📊 KONVERSIYA</b>",
            f"Jami userlar: <b>{snapshot.get('total_users', 0)}</b>",
            f"To'lov qilganlar: <b>{snapshot.get('paid_users', 0)}</b>",
            f"Konversiya: <b>{conv}%</b>",
            f"CV: <b>{snapshot.get('cv_total', 0)}</b> | "
            f"Obyektivka: <b>{snapshot.get('obyektivka_total', 0)}</b>",
            "",
            "<b>🏆 TOP FOYDALANUVCHILAR</b>",
        ]
    )
    top = snapshot.get("top_users") or []
    if top:
        for i, row in enumerate(top, 1):
            uname = html.escape(format_username(row.get("username")))
            cnt = int(row.get("approved_count") or 0)
            lines.append(f"{i}. {uname} — <b>{cnt}</b> ta xarid")
    else:
        lines.append("<i>Hali ma'lumot yo'q</i>")

    return "\n".join(lines)


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
    try:
        snapshot = await asyncio.to_thread(stats_repo.dashboard_snapshot)
        text = build_dashboard_text(snapshot)
        msg = await bot.send_message(chat_id, text)
    except Exception as exc:
        logger.exception("Dashboard start failed: %s", exc)
        msg = await bot.send_message(
            chat_id,
            "❌ Dashboard yuklanmadi. /admin ni qayta bosing yoki «🔄 Dashboard» tugmasini bosing.",
        )
        return msg.message_id
    session = DashboardSession(admin_id=admin_id, chat_id=chat_id, message_id=msg.message_id)
    session.task = asyncio.create_task(_refresh_loop(bot, session), name=f"dash_{admin_id}")
    _sessions[admin_id] = session
    return msg.message_id
