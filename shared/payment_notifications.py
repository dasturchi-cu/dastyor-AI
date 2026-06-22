"""Admin / support payment notification formatting."""
from __future__ import annotations

import html
import re
from typing import Any

from config.settings import settings


def purchase_ordinal(n: int) -> str:
    """Return e.g. '5th purchase' for n=5."""
    n = int(n)
    if n < 1:
        return "—"
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix} purchase"


def format_username(username: str | None) -> str:
    u = (username or "").strip().lstrip("@")
    return f"@{u}" if u else "No Username"


def format_document_type(kind: str | None, payment: dict[str, Any] | None = None) -> str:
    raw = (payment or {}).get("document_type") or kind or ""
    key = str(raw).strip().lower()
    labels = {
        "cv": "CV",
        "obyektivka": "Obyektivka",
        "oby": "Obyektivka",
        "manual": "Manual",
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
    amount = f"{settings.single_doc_price_uzs:,} UZS"

    user_line = full_name
    if telegram_id:
        user_line = f'<a href="tg://user?id={telegram_id}">{full_name}</a>'

    header = "✅ AUTO-APPROVED PAYMENT" if auto_approved else "💳 NEW PAYMENT"
    lines = [
        f"<b>{header}</b>",
        "",
        "Payment ID:",
        f"#{pid}",
        "",
        "User:",
        user_line,
        "",
        "Username:",
        username,
        "",
        "User ID:",
        f"<code>{telegram_id}</code>" if telegram_id else "—",
        "",
        "Purchase Number:",
        html.escape(purchase_ordinal(purchase_number)),
        "",
        "Document:",
        document,
        "",
        "Amount:",
        amount,
        "",
        "Date:",
        date_s,
        "",
        "Time:",
        time_s,
    ]
    if auto_approved:
        lines.extend(["", "Credits balance:", f"<b>{credits}</b>"])
    return "\n".join(lines)


def build_pending_payments_list(payments: list[dict[str, Any]]) -> str:
    if not payments:
        return ""
    lines = ["<b>Pending payments</b>", ""]
    lines.extend(payment_list_line(p) for p in payments)
    return "\n".join(lines)
