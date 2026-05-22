"""Admin broadcast — barcha bot foydalanuvchilariga xabar + hisobot."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from collections import Counter
from datetime import datetime

from telegram import Bot
from telegram.error import BadRequest, Forbidden, RetryAfter

logger = logging.getLogger(__name__)

BROADCAST_LOG_FILE = os.getenv("BROADCAST_LOG_FILE", "broadcast_logs.json")
_SEND_DELAY = float(os.getenv("BROADCAST_SEND_DELAY_SECONDS", "0.04") or "0.04")

def collect_broadcast_recipients() -> list[tuple[int, int]]:
    """(user_id, chat_id) — banlanganlar tashqari."""
    from bot.services.user_service import get_all_profiles

    profiles = get_all_profiles() or {}
    out: list[tuple[int, int]] = []
    seen: set[int] = set()
    for uid_str, p in profiles.items():
        if not isinstance(p, dict):
            continue
        if p.get("is_banned"):
            continue
        try:
            uid = int(p.get("id") or uid_str)
            chat_id = int(p.get("chat_id") or uid)
        except (TypeError, ValueError):
            continue
        if uid in seen:
            continue
        seen.add(uid)
        out.append((uid, chat_id))
    return out


def _classify_error(exc: BaseException) -> str:
    if isinstance(exc, Forbidden):
        return "Bot bloklangan"
    if isinstance(exc, BadRequest):
        msg = str(exc).lower()
        if "chat not found" in msg or "peer_id_invalid" in msg:
            return "Chat topilmadi"
        if "parse" in msg or "can't find end" in msg:
            return "Matn (HTML) xato"
        if "blocked" in msg:
            return "Bot bloklangan"
        return "Telegram rad etdi"
    return "Noma'lum xato"


async def _send_one(bot: Bot, chat_id: int, text: str, *, parse_mode: str) -> None:
    await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)


async def run_broadcast(
    bot: Bot,
    text: str,
    *,
    parse_mode: str = "HTML",
    progress_chat_id: int | None = None,
) -> dict:
    """
    Hammaga yuborish. Natija: ok, fail, total, reasons, failed_samples.
    """
    from bot.services.user_service import set_user_blocked_bot

    recipients = collect_broadcast_recipients()
    total = len(recipients)
    ok = 0
    fail = 0
    reasons: Counter[str] = Counter()
    failed_samples: list[str] = []

    for i, (uid, chat_id) in enumerate(recipients, start=1):
        sent = False
        last_err: BaseException | None = None
        for attempt in range(2):
            try:
                await _send_one(bot, chat_id, text, parse_mode=parse_mode)
                ok += 1
                sent = True
                break
            except RetryAfter as e:
                wait = float(getattr(e, "retry_after", 3) or 3) + 0.5
                await asyncio.sleep(wait)
                last_err = e
            except Forbidden as e:
                last_err = e
                set_user_blocked_bot(uid, blocked=True)
                break
            except BadRequest as e:
                last_err = e
                break
            except Exception as e:
                last_err = e
                break
        if not sent:
            fail += 1
            reason = _classify_error(last_err) if last_err else "Noma'lum xato"
            reasons[reason] += 1
            if len(failed_samples) < 8:
                failed_samples.append(f"<code>{uid}</code> — {reason}")

        if progress_chat_id and i % 25 == 0:
            try:
                await bot.send_message(
                    chat_id=progress_chat_id,
                    text=f"⏳ Yuborilmoqda… {i}/{total}",
                )
            except Exception:
                pass
        await asyncio.sleep(_SEND_DELAY)

    result = {
        "total": total,
        "ok": ok,
        "fail": fail,
        "reasons": dict(reasons),
        "failed_samples": failed_samples,
        "finished_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _append_log(result, text[:200])
    return result


def format_broadcast_report(result: dict) -> str:
    total = int(result.get("total") or 0)
    ok = int(result.get("ok") or 0)
    fail = int(result.get("fail") or 0)
    lines = [
        "📢 <b>Yuborish tugadi</b>",
        "",
        f"👥 Jami ro‘yxat: <b>{total}</b>",
        f"✅ Yetdi: <b>{ok}</b>",
        f"❌ Yetmadi: <b>{fail}</b>",
    ]
    reasons = result.get("reasons") or {}
    if reasons:
        lines.append("")
        lines.append("<b>Sabablar:</b>")
        for reason, cnt in sorted(reasons.items(), key=lambda x: -x[1]):
            lines.append(f"• {reason}: <b>{cnt}</b>")
    samples = result.get("failed_samples") or []
    if samples:
        lines.append("")
        lines.append("<b>Namuna (ID):</b>")
        lines.extend(samples[:6])
    lines.append("")
    lines.append(f"🕐 {result.get('finished_at', '')}")
    return "\n".join(lines)


def _append_log(result: dict, text_preview: str) -> None:
    try:
        rows = []
        if os.path.exists(BROADCAST_LOG_FILE):
            with open(BROADCAST_LOG_FILE, "r", encoding="utf-8") as f:
                rows = json.load(f)
        if not isinstance(rows, list):
            rows = []
        rows.append(
            {
                "at": result.get("finished_at"),
                "preview": text_preview,
                "total": result.get("total"),
                "ok": result.get("ok"),
                "fail": result.get("fail"),
                "reasons": result.get("reasons"),
            }
        )
        rows = rows[-50:]
        with open(BROADCAST_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("broadcast log write failed: %s", e)
