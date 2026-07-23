"""Referral program copy and referrer notifications."""
from __future__ import annotations

from typing import Any

from shared.marketing import format_price_uzs


def referral_balance_block(ref_link: str, progress: dict[str, Any]) -> str:
    paid = int(progress.get("paid_count") or 0)
    price = format_price_uzs()
    return (
        f"🎁 Do'stingiz to'lov qilsa ({price}+ so'm) — sizga <b>+1</b>.\n"
        f"To'lagan do'stlar: <b>{paid}</b>\n"
        f"<code>{ref_link}</code>"
    )


def referrer_reward_message(ref_info: dict[str, Any]) -> str:
    if ref_info.get("rewarded"):
        added = int(ref_info.get("credits_added") or 1)
        return f"🎉 Do'stingiz to'ladi — sizga <b>+{added}</b> yuklash!"
    return "👥 Do'stingiz hujjat yukladi. U to'lasa — sizga +1."


def referrer_paid_progress_message(ref_info: dict[str, Any]) -> str:
    if ref_info.get("rewarded"):
        return referrer_reward_message(ref_info)
    return "💳 Do'stingiz to'lov qildi — balansni tekshiring."


async def notify_referrer(bot, ref_info: dict[str, Any] | None, *, event: str = "download") -> None:
    if not bot or not ref_info:
        return
    ref_id = int(ref_info.get("referrer_id") or 0)
    if not ref_id:
        return
    if event == "payment":
        text = referrer_paid_progress_message(ref_info)
    else:
        text = referrer_reward_message(ref_info)
    try:
        await bot.send_message(chat_id=ref_id, text=text)
    except Exception:
        pass
