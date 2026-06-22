"""Admin panel business logic."""
from __future__ import annotations

import asyncio
import html
import tempfile
from pathlib import Path
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError

from config.settings import settings
from database.repositories import admin_stats as stats_repo
from database.repositories import users as users_repo
from shared.payment_notifications import format_username


def display_name(user: dict[str, Any]) -> str:
    first = str(user.get("first_name") or "").strip()
    last = str(user.get("last_name") or "").strip()
    combined = f"{first} {last}".strip()
    return combined or str(user.get("payer_name") or "—")


def build_profile_text(profile: dict[str, Any]) -> str:
    tid = int(profile.get("telegram_id") or 0)
    name = html.escape(display_name(profile))
    username = html.escape(format_username(profile.get("username")))
    blocked = bool(int(profile.get("is_blocked") or 0))
    user_line = (
        f'<a href="tg://user?id={tid}">{name}</a>' if tid else name
    )
    return (
        f"<b>👤 Foydalanuvchi profili</b>\n\n"
        f"ID: <code>{tid}</code>\n"
        f"Username: {username}\n"
        f"Ism: {user_line}\n"
        f"Ro'yxatdan o'tgan: {profile.get('created_at') or '—'}\n"
        f"CV soni: <b>{profile.get('cv_count', 0)}</b>\n"
        f"Obyektivka soni: <b>{profile.get('obyektivka_count', 0)}</b>\n"
        f"To'lovlar soni: <b>{profile.get('payments_count', 0)}</b>\n"
        f"Kredit: <b>{profile.get('credits', 0)}</b>\n"
        f"Oxirgi aktivlik: {profile.get('last_activity') or '—'}\n"
        f"Holat: {'🚫 Bloklangan' if blocked else '✅ Faol'}"
    )


def build_today_stats_text() -> str:
    s = stats_repo.today_stats()
    return (
        f"<b>📊 Bugungi statistika</b>\n\n"
        f"Yangi userlar: <b>{s['new_users']}</b>\n"
        f"To'lovlar: <b>{s['payments']}</b>\n"
        f"Tasdiqlangan: <b>{s['approved_payments']}</b>\n"
        f"CV: <b>{s['cv']}</b>\n"
        f"Obyektivka: <b>{s['obyektivka']}</b>\n"
        f"Tushum: <b>{s['revenue_uzs']:,} UZS</b>"
    )


def build_top_users_text(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "Hali to'lov qilgan foydalanuvchilar yo'q."
    lines = ["<b>🏆 TOP 10 — ko'p to'lov qilganlar</b>\n"]
    for i, row in enumerate(rows, 1):
        tid = int(row.get("telegram_id") or 0)
        name = html.escape(display_name(row))
        username = html.escape(format_username(row.get("username")))
        approved = int(row.get("approved_count") or 0)
        total = int(row.get("payment_count") or 0)
        lines.append(
            f"{i}. {name} ({username})\n"
            f"   ID: <code>{tid}</code> | ✅ {approved} / jami {total}"
        )
    return "\n".join(lines)


def build_error_log_text(rows: list[dict[str, Any]], *, title: str = "Oxirgi xatolar") -> str:
    if not rows:
        return f"<b>⚠️ {title}</b>\n\nXatolar yo'q."
    lines = [f"<b>⚠️ {title}</b>\n"]
    for row in rows[:15]:
        cat = html.escape(str(row.get("category") or "general"))
        msg = html.escape(str(row.get("message") or "")[:200])
        ts = row.get("created_at") or ""
        lines.append(f"• [{cat}] {msg}\n  <i>{ts}</i>")
    return "\n".join(lines)


async def run_broadcast(bot: Bot, text: str) -> dict[str, int]:
    targets = users_repo.list_broadcast_targets()
    sent = success = blocked = 0
    for tid in targets:
        sent += 1
        try:
            await bot.send_message(tid, text)
            success += 1
        except TelegramForbiddenError:
            blocked += 1
        except Exception:
            pass
        if sent % 25 == 0:
            await asyncio.sleep(1)
        else:
            await asyncio.sleep(0.04)
    return {"sent": sent, "success": success, "blocked": blocked}


def _write_xlsx(headers: list[str], rows: list[list[Any]], path: Path) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(path)


def build_users_xlsx() -> Path:
    rows = stats_repo.export_users_rows()
    path = Path(tempfile.gettempdir()) / "Users.xlsx"
    data = [
        [
            r.get("telegram_id"),
            r.get("username"),
            r.get("first_name"),
            r.get("last_name"),
            r.get("credits"),
            r.get("payments_count"),
            r.get("cv_count"),
            r.get("oby_count"),
            r.get("is_blocked"),
            r.get("created_at"),
            r.get("last_active_at"),
        ]
        for r in rows
    ]
    _write_xlsx(
        [
            "telegram_id",
            "username",
            "first_name",
            "last_name",
            "credits",
            "payments",
            "cv",
            "obyektivka",
            "blocked",
            "registered",
            "last_active",
        ],
        data,
        path,
    )
    return path


def build_payments_xlsx() -> Path:
    rows = stats_repo.export_payments_rows()
    path = Path(tempfile.gettempdir()) / "Payments.xlsx"
    data = [
        [
            r.get("id"),
            r.get("telegram_id"),
            r.get("username"),
            r.get("payer_name"),
            r.get("document_type"),
            r.get("status"),
            r.get("card_number"),
            r.get("created_at"),
        ]
        for r in rows
    ]
    _write_xlsx(
        [
            "payment_id",
            "telegram_id",
            "username",
            "payer_name",
            "document_type",
            "status",
            "card_number",
            "created_at",
        ],
        data,
        path,
    )
    return path


def build_statistics_xlsx() -> Path:
    rows = stats_repo.export_statistics_rows()
    path = Path(tempfile.gettempdir()) / "Statistics.xlsx"
    data = [
        [
            r.get("period"),
            r.get("new_users"),
            r.get("payments"),
            r.get("approved_payments"),
            r.get("cv"),
            r.get("obyektivka"),
            r.get("revenue_uzs"),
        ]
        for r in rows
    ]
    _write_xlsx(
        [
            "period",
            "new_users",
            "payments",
            "approved_payments",
            "cv",
            "obyektivka",
            "revenue_uzs",
        ],
        data,
        path,
    )
    return path
