"""Admin panel matn formatlari — faqat SQLite ma'lumotlari."""
from __future__ import annotations

import html
from typing import Any

from features.admin.service import display_name
from shared.payment_notifications import format_document_type, format_username


def build_dashboard_text(metrics: dict[str, Any], *, updated_at: str) -> str:
    from features.admin.dashboard import _feed_line

    revenue = int(metrics.get("revenue_uzs") or 0)
    lines = [
        "<b>🛠 ADMIN DASHBOARD</b>",
        f"<i>🔄 {updated_at} | SQLite real-time</i>",
        "",
        f"👥 Foydalanuvchilar: <b>{metrics.get('users_count', 0)}</b>",
        f"💳 Kutilayotgan: <b>{metrics.get('pending_payments', 0)}</b>",
        f"✅ Tasdiqlangan: <b>{metrics.get('approved_payments', 0)}</b>",
        f"❌ Rad etilgan: <b>{metrics.get('rejected_payments', 0)}</b>",
        f"📄 CV: <b>{metrics.get('cv_total', 0)}</b>",
        f"📋 Obyektivka: <b>{metrics.get('obyektivka_total', 0)}</b>",
        f"💰 Tushum: <b>{revenue:,} so'm</b>",
        f"🔥 Faol (bugun): <b>{metrics.get('active_users', 0)}</b>",
        "",
        "<b>🔥 JONLI TA'MINOT</b>",
    ]
    feed = metrics.get("feed") or []
    if feed:
        for ev in feed[:6]:
            lines.append(f"• {_feed_line(ev)}")
    else:
        lines.append("<i>Faollik yozuvlari yo'q</i>")
    lines.extend(
        [
            "",
            "<b>📊 KONVERSIYA</b>",
            f"To'lov qilganlar: <b>{metrics.get('paid_users', 0)}</b>",
            f"Konversiya: <b>{metrics.get('conversion_pct', 0)}%</b>",
            "",
            "<b>📈 BUGUN</b>",
            f"Yangi userlar: <b>{metrics.get('new_users_today', 0)}</b>",
            f"CV: <b>{metrics.get('cv_today', 0)}</b> | "
            f"Obyektivka: <b>{metrics.get('obyektivka_today', 0)}</b>",
            f"Tushum: <b>{int(metrics.get('revenue_today_uzs') or 0):,} so'm</b>",
        ]
    )
    top = metrics.get("top_users") or []
    if top:
        lines.extend(["", "<b>🏆 TOP (xarid)</b>"])
        for i, row in enumerate(top, 1):
            uname = html.escape(format_username(row.get("username")))
            cnt = int(row.get("approved_count") or 0)
            lines.append(f"{i}. {uname} — <b>{cnt}</b>")
    return "\n".join(lines)


def build_users_list_text(rows: list[dict[str, Any]], *, total: int) -> str:
    if not rows:
        return "👥 SQLite: foydalanuvchilar yo'q."
    lines = [f"<b>👥 Foydalanuvchilar</b> (jami: {total}, ko'rsatilmoqda: {len(rows)})\n"]
    for u in rows:
        tid = int(u.get("telegram_id") or 0)
        name = html.escape(display_name(u))
        uname = html.escape(format_username(u.get("username")))
        lines.append(
            f"━━━━━━━━━━━━━━\n"
            f"ID: <code>{tid}</code>\n"
            f"Ism: {name}\n"
            f"Username: {uname}\n"
            f"Ro'yxatdan: {u.get('created_at') or '—'}\n"
            f"Oxirgi aktivlik: {u.get('last_activity') or '—'}\n"
            f"Xaridlar: <b>{u.get('payments_count', 0)}</b> | "
            f"CV: <b>{u.get('cv_count', 0)}</b> | "
            f"Oby: <b>{u.get('obyektivka_count', 0)}</b>"
        )
    return "\n".join(lines)


def build_payments_list_text(rows: list[dict[str, Any]], *, title: str) -> str:
    if not rows:
        return f"💳 {title}: to'lovlar topilmadi."
    lines = [f"<b>💳 {title}</b> ({len(rows)} ta)\n"]
    for p in rows:
        pid = int(p.get("id") or 0)
        name = html.escape(display_name(p))
        uname = html.escape(format_username(p.get("username")))
        doc = html.escape(format_document_type(None, p))
        status = html.escape(str(p.get("status") or "—"))
        amount = int(p.get("amount_uzs") or 0)
        lines.append(
            f"━━━━━━━━━━━━━━\n"
            f"#{pid} | {status}\n"
            f"Foydalanuvchi: {name}\n"
            f"Username: {uname}\n"
            f"User ID: <code>{p.get('telegram_id')}</code>\n"
            f"Hujjat: {doc}\n"
            f"Summa: <b>{amount:,} so'm</b>\n"
            f"Vaqt: {p.get('created_at') or '—'}"
        )
    return "\n".join(lines)


def build_statistics_text(metrics: dict[str, Any]) -> str:
    return (
        f"<b>📊 Statistika (SQLite)</b>\n\n"
        f"<b>JAMI</b>\n"
        f"Foydalanuvchilar: <b>{metrics.get('users_count', 0)}</b>\n"
        f"To'lovlar: <b>{metrics.get('payments_total', 0)}</b>\n"
        f"✅ Tasdiqlangan: <b>{metrics.get('approved_payments', 0)}</b>\n"
        f"⏳ Kutilayotgan: <b>{metrics.get('pending_payments', 0)}</b>\n"
        f"❌ Rad etilgan: <b>{metrics.get('rejected_payments', 0)}</b>\n"
        f"CV: <b>{metrics.get('cv_total', 0)}</b>\n"
        f"Obyektivka: <b>{metrics.get('obyektivka_total', 0)}</b>\n"
        f"Tushum: <b>{int(metrics.get('revenue_uzs') or 0):,} so'm</b>\n"
        f"Konversiya: <b>{metrics.get('conversion_pct', 0)}%</b>\n\n"
        f"<b>BUGUN</b>\n"
        f"Yangi userlar: <b>{metrics.get('new_users_today', 0)}</b>\n"
        f"CV: <b>{metrics.get('cv_today', 0)}</b>\n"
        f"Obyektivka: <b>{metrics.get('obyektivka_today', 0)}</b>\n"
        f"Tasdiqlangan: <b>{metrics.get('approved_today', 0)}</b>\n"
        f"Tushum: <b>{int(metrics.get('revenue_today_uzs') or 0):,} so'm</b>"
    )


def build_top_users_report(report: dict[str, list[dict[str, Any]]]) -> str:
    lines = ["<b>🏆 TOP FOYDALANUVCHILAR</b>\n"]

    purchases = report.get("by_purchases") or []
    lines.append("<b>💳 Ko'p xarid qilganlar</b>")
    if purchases:
        for i, r in enumerate(purchases, 1):
            uname = html.escape(format_username(r.get("username")))
            cnt = int(r.get("approved_count") or 0)
            lines.append(f"{i}. {uname} — <b>{cnt}</b> ta tasdiqlangan")
    else:
        lines.append("<i>Ma'lumot yo'q</i>")

    docs = report.get("by_documents") or []
    lines.append("\n<b>📄 Ko'p hujjat yaratganlar</b>")
    if docs:
        for i, r in enumerate(docs, 1):
            uname = html.escape(format_username(r.get("username")))
            total = int(r.get("docs_total") or 0)
            lines.append(f"{i}. {uname} — <b>{total}</b> ta hujjat")
    else:
        lines.append("<i>Ma'lumot yo'q</i>")

    active = report.get("by_activity") or []
    lines.append("\n<b>🔥 Eng faol userlar</b>")
    if active:
        for i, r in enumerate(active, 1):
            uname = html.escape(format_username(r.get("username")))
            la = r.get("last_activity") or "—"
            lines.append(f"{i}. {uname} — {la}")
    else:
        lines.append("<i>Ma'lumot yo'q</i>")

    return "\n".join(lines)
