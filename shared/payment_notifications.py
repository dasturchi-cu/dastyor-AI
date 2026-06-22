"""Admin / support payment notification formatting (O'zbek)."""
from __future__ import annotations

import html
import re
from typing import Any

from config.settings import settings


def purchase_ordinal_uz(n: int) -> str:
    """Masalan: 5 → '5-chi xarid'."""
    n = int(n)
    if n < 1:
        return "—"
    return f"{n}-chi xarid"


def purchase_ordinal(n: int) -> str:
    return purchase_ordinal_uz(n)


def format_username(username: str | None) -> str:
    u = (username or "").strip().lstrip("@")
    return f"@{u}" if u else "Username yo'q"


def format_document_type(kind: str | None, payment: dict[str, Any] | None = None) -> str:
    raw = (payment or {}).get("document_type") or kind or ""
    key = str(raw).strip().lower()
    labels = {
        "cv": "CV",
        "obyektivka": "Obyektivka",
        "oby": "Obyektivka",
        "manual": "Qo'lda",
    }
    return labels.get(key, raw.title() if raw else "—")


def full_name_from_payment(payment: dict[str, Any]) -> str:
    first = str(payment.get("first_name") or "").strip()
    last = str(payment.get("last_name") or "").strip()
    combined = f"{first} {last}".strip()
    if combined:
        return combined
    return str(payment.get("payer_name") or "—").strip()


def split_datetime(created_at: str | None) -> tuple[str, str]:
    if not created_at:
        return "—", "—"
    text = str(created_at).strip()
    if "T" in text:
        date_part, time_part = text.split("T", 1)
        time_part = time_part[:8]
        return date_part[:10], time_part[:5]
    match = re.match(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})", text)
    if match:
        return match.group(1), match.group(2)
    return text[:10], "—"


def payment_list_line(payment: dict[str, Any]) -> str:
    pid = int(payment["id"])
    username = format_username(payment.get("username"))
    name = html.escape(full_name_from_payment(payment))
    return f"#{pid} | {html.escape(username)} | {name}"


def build_payment_notification_text(
    payment: dict[str, Any],
    *,
    kind: str,
    purchase_number: int,
    auto_approved: bool = False,
    credits: int = 0,
) -> str:
    pid = int(payment["id"])
    telegram_id = int(payment.get("telegram_id") or 0)
    full_name = html.escape(full_name_from_payment(payment))
    username = html.escape(format_username(payment.get("username")))
    document = html.escape(format_document_type(kind, payment))
    date_s, time_s = split_datetime(payment.get("created_at"))
    amount = f"{settings.single_doc_price_uzs:,} so'm"

    user_line = full_name
    if telegram_id:
        user_line = f'<a href="tg://user?id={telegram_id}">{full_name}</a>'

    header = "✅ AVTOMATIK TASDIQLANDI" if auto_approved else "💳 YANGI TO'LOV"
    lines = [
        f"<b>{header}</b>",
        "",
        "To'lov ID:",
        f"#{pid}",
        "",
        "Foydalanuvchi:",
        user_line,
        "",
        "Username:",
        username,
        "",
        "User ID:",
        f"<code>{telegram_id}</code>" if telegram_id else "—",
        "",
        "Xarid raqami:",
        html.escape(purchase_ordinal_uz(purchase_number)),
        "",
        "Hujjat turi:",
        document,
        "",
        "Summa:",
        amount,
        "",
        "Sana:",
        date_s,
        "",
        "Vaqt:",
        time_s,
    ]
    if auto_approved:
        lines.extend(["", "Kredit balansi:", f"<b>{credits}</b>"])
    return "\n".join(lines)


def build_pending_payments_list(payments: list[dict[str, Any]]) -> str:
    if not payments:
        return ""
    lines = ["<b>Kutilayotgan to'lovlar</b>", ""]
    lines.extend(payment_list_line(p) for p in payments)
    return "\n".join(lines)


def build_daily_admin_report(stats: dict[str, Any], *, report_date: str) -> str:
    revenue = int(stats.get("revenue_uzs") or 0)
    conv = stats.get("conversion_pct", 0)
    return (
        f"<b>📊 Kunlik hisobot — {html.escape(report_date)}</b>\n\n"
        f"Yangi userlar: <b>{stats.get('new_users', 0)}</b>\n"
        f"CV soni: <b>{stats.get('cv', 0)}</b>\n"
        f"Obyektivka soni: <b>{stats.get('obyektivka', 0)}</b>\n"
        f"Tushum: <b>{revenue:,} so'm</b>\n"
        f"Kutilayotgan to'lovlar: <b>{stats.get('pending_payments', 0)}</b>\n"
        f"Tasdiqlangan to'lovlar: <b>{stats.get('approved_payments', 0)}</b>\n"
        f"Konversiya: <b>{conv}%</b>"
    )


def build_pending_payment_reminder(payment: dict[str, Any], *, hours_pending: int) -> str:
    pid = int(payment["id"])
    telegram_id = int(payment.get("telegram_id") or 0)
    full_name = html.escape(full_name_from_payment(payment))
    username = html.escape(format_username(payment.get("username")))
    document = html.escape(format_document_type(None, payment))
    date_s, time_s = split_datetime(payment.get("created_at"))
    user_line = full_name
    if telegram_id:
        user_line = f'<a href="tg://user?id={telegram_id}">{full_name}</a>'
    return (
        f"<b>⚠️ Kutilayotgan to'lov</b>\n\n"
        f"To'lov ID: #{pid}\n"
        f"Kutilmoqda: <b>{hours_pending}+ soat</b>\n\n"
        f"Foydalanuvchi: {user_line}\n"
        f"Username: {username}\n"
        f"User ID: <code>{telegram_id}</code>\n"
        f"Hujjat: {document}\n"
        f"Yuborilgan: {date_s} {time_s}"
    )


def build_returning_customer_alert(
    payment: dict[str, Any],
    *,
    kind: str,
    purchase_number: int,
    previous_approved: int,
) -> str:
    telegram_id = int(payment.get("telegram_id") or 0)
    full_name = html.escape(full_name_from_payment(payment))
    username = html.escape(format_username(payment.get("username")))
    user_line = full_name
    if telegram_id:
        user_line = f'<a href="tg://user?id={telegram_id}">{full_name}</a>'
    return (
        f"<b>🔥 QAYTA MIJOZ</b>\n\n"
        f"Ism: {user_line}\n"
        f"Username: {username}\n"
        f"Xarid: {html.escape(purchase_ordinal_uz(purchase_number))}\n"
        f"Oldingi tasdiqlangan: <b>{previous_approved}</b>\n"
        f"To'lov ID: #{int(payment['id'])}"
    )
