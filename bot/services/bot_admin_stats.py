"""Admin panel uchun qisqa statistika (schema o‘zgartirmasdan)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def _count_table_status(table: str, status: str) -> int | None:
    try:
        from bot.services.supabase_db import _get_client

        c = _get_client()
        if not c:
            return None
        r = (
            c.table(table)
            .select("id", count="exact")
            .eq("status", status)
            .limit(1)
            .execute()
        )
        return int(getattr(r, "count", None) or 0)
    except Exception as e:
        logger.debug("count %s.%s: %s", table, status, e)
        return None


def _count_users_active_days(days: int = 7) -> int | None:
    try:
        from bot.services.supabase_db import db_get_all_users

        users = db_get_all_users()
        if not users:
            return 0
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        n = 0
        for row in users.values():
            la = row.get("last_active")
            if not la:
                continue
            try:
                if isinstance(la, str):
                    ts = datetime.fromisoformat(la.replace("Z", "+00:00"))
                else:
                    continue
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts >= cutoff:
                    n += 1
            except Exception:
                continue
        return n
    except Exception as e:
        logger.debug("active users: %s", e)
        return None


def format_admin_stats_text() -> str:
    lines = ["📊 <b>Bot statistikasi</b>\n"]

    try:
        from bot.services.supabase_db import has_db

        if not has_db():
            lines.append("⚠️ Supabase ulanmagan — raqamlar mavjud emas.")
            return "\n".join(lines)
    except Exception:
        lines.append("⚠️ Ma’lumotlar bazasiga ulanib bo‘lmadi.")
        return "\n".join(lines)

    try:
        from bot.services.supabase_db import db_get_all_users

        total = len(db_get_all_users())
        lines.append(f"👥 Foydalanuvchilar: <b>{total}</b>")
    except Exception:
        lines.append("👥 Foydalanuvchilar: —")

    active7 = _count_users_active_days(7)
    if active7 is not None:
        lines.append(f"🟢 Faol (7 kun): <b>{active7}</b>")

    pending_pay = _count_table_status("payments", "pending")
    if pending_pay is not None:
        lines.append(f"💳 Kutilayotgan to‘lovlar: <b>{pending_pay}</b>")

    pending_doc = _count_table_status("paid_doc_requests", "pending")
    if pending_doc is not None:
        lines.append(f"📄 Kutilayotgan CV/Oby (5k): <b>{pending_doc}</b>")

    try:
        from bot.services.support_service import support_stats

        ss = support_stats()
        lines.append(
            f"📨 Murojaatlar: jami <b>{ss.get('total', 0)}</b>, "
            f"ochiq <b>{ss.get('open', 0)}</b>"
        )
    except Exception:
        pass

    lines.append("\n<i>To‘lovlar guruhi va murojaatlar paneli — tegishli tugmalar orqali.</i>")
    return "\n".join(lines)


async def send_daily_admin_digest(bot, admin_chat_id: int) -> None:
    """Admin guruhiga kunlik qisqa hisobot (startup yoki tugma)."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    text = f"📋 <b>Kunlik hisobot</b> · {now}\n\n{format_admin_stats_text()}"
    try:
        await bot.send_message(chat_id=int(admin_chat_id), text=text, parse_mode="HTML")
    except Exception as e:
        logger.warning("daily digest failed chat=%s: %s", admin_chat_id, e)
