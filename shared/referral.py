"""Referral program copy and referrer notifications."""
from __future__ import annotations

from typing import Any

from shared.marketing import format_price_uzs


def referral_balance_block(ref_link: str, progress: dict[str, Any]) -> str:
    active = int(progress.get("active_count") or 0)
    paid = int(progress.get("paid_count") or 0)
    price = format_price_uzs()

    return (
        f"👥 <b>Faol takliflaringiz:</b> {active} ta "
        f"(hujjat yuklab olgan do'stlar)\n"
        f"💳 <b>To'lov qilgan takliflar:</b> {paid} ta\n\n"
        "🎁 <b>Referral dasturi (sodda)</b>\n"
        "Do'stingizga havolangizni yuboring.\n"
        f"U <b>bir marta to'lov</b> qilsa ({price} so'm dan) — sizga <b>+1 bepul yuklash</b>.\n"
        f"🔗 <b>Sizning havolangiz:</b>\n<code>{ref_link}</code>"
    )


def referrer_reward_message(ref_info: dict[str, Any]) -> str:
    if ref_info.get("rewarded"):
        added = int(ref_info.get("credits_added") or 1)
        return (
            "🎉 <b>Tabriklaymiz!</b>\n\n"
            "Taklif qilgan do'stingiz to'lov qildi.\n\n"
            f"Sizga <b>+{added} ta bepul yuklash</b> taqdim etildi! 💳"
        )

    return (
        "👥 <b>Yangi faol taklif!</b>\n\n"
        "Do'stingiz birinchi hujjatini yuklab oldi.\n"
        "U to'lov qilganda sizga <b>+1 bepul yuklash</b> beriladi."
    )


def referrer_paid_progress_message(ref_info: dict[str, Any]) -> str:
    if ref_info.get("rewarded"):
        return referrer_reward_message(ref_info)
    return (
        "💳 <b>Taklif qilgan do'stingiz to'lov qildi!</b>\n\n"
        "Mukofot hisoblanmoqda — balansni tekshiring."
    )


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
