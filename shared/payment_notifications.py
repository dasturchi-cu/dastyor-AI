"""Admin / support payment notification formatting (O'zbek)."""
from __future__ import annotations

import html
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

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
        "cv": "CV Resume",
        "obyektivka": "Obyektivka",
        "oby": "Obyektivka",
        "cover": "Muqova xati",
        "translate": "Hujjat tarjimasi",
        "manual": "Qo'lda",
    }
    return labels.get(key, raw.title() if raw else "—")


def normalize_payment_service(document_type: str | None) -> str:
    key = str(document_type or "cv").strip().lower()
    if key == "oby":
        return "obyektivka"
    if key in {"cv", "obyektivka", "cover", "translate"}:
        return key
    return "cv"


def payment_service_command(document_type: str | None) -> str:
    service = normalize_payment_service(document_type)
    return {
        "cv": "/cv",
        "obyektivka": "/obyektivka",
        "cover": "/cover",
        "translate": "/translate",
    }.get(service, "/cv")


def full_name_from_payment(payment: dict[str, Any]) -> str:
    first = str(payment.get("first_name") or "").strip()
    last = str(payment.get("last_name") or "").strip()
    combined = f"{first} {last}".strip()
    if combined:
        return combined
    return str(payment.get("payer_name") or "—").strip()


def _report_tz() -> ZoneInfo:
    try:
        return ZoneInfo(settings.admin_report_timezone or "Asia/Tashkent")
    except Exception:
        return ZoneInfo("Asia/Tashkent")


def _parse_utc_datetime(text: str) -> datetime | None:
    raw = text.strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    if "T" in raw:
        try:
            dt = datetime.fromisoformat(raw[:26])
            if dt.tzinfo is None:
                return dt.replace(tzinfo=ZoneInfo("UTC"))
            return dt.astimezone(ZoneInfo("UTC"))
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(raw[:19], fmt)
            return dt.replace(tzinfo=ZoneInfo("UTC"))
        except ValueError:
            continue
    match = re.match(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})", raw)
    if match:
        try:
            dt = datetime.strptime(f"{match.group(1)} {match.group(2)}", "%Y-%m-%d %H:%M")
            return dt.replace(tzinfo=ZoneInfo("UTC"))
        except ValueError:
            return None
    return None


def split_datetime(created_at: str | None) -> tuple[str, str]:
    """SQLite UTC vaqtini O'zbekiston (Toshkent) vaqtiga o'giradi."""
    if not created_at:
        return "—", "—"
    dt = _parse_utc_datetime(str(created_at))
    if dt is None:
        text = str(created_at).strip()
        return text[:10], "—"
    local = dt.astimezone(_report_tz())
    return local.strftime("%d.%m.%Y"), local.strftime("%H:%M")


def format_datetime_uz(created_at: str | None) -> str:
    date_s, time_s = split_datetime(created_at)
    if date_s == "—":
        return "—"
    return f"{date_s}, {time_s}"


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
    rejected: bool = False,
    credits: int = 0,
) -> str:
    pid = int(payment["id"])
    telegram_id = int(payment.get("telegram_id") or 0)
    full_name = html.escape(full_name_from_payment(payment))
    username = html.escape(format_username(payment.get("username")))
    document = html.escape(format_document_type(kind, payment))
    when = html.escape(format_datetime_uz(payment.get("created_at")))
    amount = f"{settings.single_doc_price_uzs:,} so'm"
    purchase = html.escape(purchase_ordinal_uz(purchase_number))

    user_line = full_name
    if telegram_id:
        user_line = f'<a href="tg://user?id={telegram_id}">{full_name}</a>'

    if rejected:
        header = f"❌ RAD ETILDI #{pid}"
    elif auto_approved:
        header = f"✅ TASDIQLANDI #{pid}"
    else:
        header = f"💳 YANGI TO'LOV #{pid}"
    lines = [
        f"<b>{header}</b>",
        "",
        f"👤 {user_line} · {username}",
        f"📄 {document} · {purchase} · {amount}",
        f"🕐 {when}",
    ]
    if auto_approved:
        lines.append(f"💳 Balans: <b>{credits}</b> ta")
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
    when = html.escape(format_datetime_uz(payment.get("created_at")))
    user_line = full_name
    if telegram_id:
        user_line = f'<a href="tg://user?id={telegram_id}">{full_name}</a>'
    return (
        f"<b>⚠️ Kutilayotgan to'lov #{pid}</b>\n"
        f"⏳ {hours_pending}+ soat kutmoqda\n\n"
        f"👤 {user_line} · {username}\n"
        f"📄 {document}\n"
        f"🕐 {when}"
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
        f"👤 {user_line} · {username}\n"
        f"📄 {html.escape(format_document_type(kind, payment))} · "
        f"{html.escape(purchase_ordinal_uz(purchase_number))}\n"
        f"Oldingi tasdiqlangan: <b>{previous_approved}</b> · "
        f"To'lov #{int(payment['id'])}"
    )
