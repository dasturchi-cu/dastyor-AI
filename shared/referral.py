"""Referral program copy and referrer notifications."""
from __future__ import annotations

from typing import Any

from shared.marketing import format_price_uzs


def referral_balance_block(ref_link: str, progress: dict[str, Any]) -> str:
    active = int(progress.get("active_count") or 0)
    paid = int(progress.get("paid_count") or 0)
    batch_progress = int(progress.get("batch_progress") or 0)
    batch_has_paid = bool(progress.get("batch_has_paid"))
    paid_mark = "✅" if batch_has_paid else "⏳"
    price = format_price_uzs()

    return (
        f"👥 <b>Faol takliflaringiz:</b> {active} ta "
        f"(hujjat yuklab olgan do'stlar)\n"
        f"💳 <b>To'lov qilgan takliflar:</b> {paid} ta\n"
        f"📊 <b>Joriy bosqich:</b> {batch_progress}/3 "
        f"(pullik xarid: {paid_mark})\n\n"
        "🎁 <b>Referral dasturi</b>\n"
        "Do'stlaringizga havolangizni ulashing. <b>+1 bepul yuklash</b> olish uchun:\n"
        "1️⃣ Taklif qilgan <b>3 nafar yangi do'stingiz</b> bot orqali birinchi hujjatini "
        "(CV yoki Obyektivka) <b>bepul yuklab olishi</b> kerak.\n"
        "2️⃣ Shu 3 ta do'stingizdan <b>kamida 1 nafari</b> kamida bir marta "
        f"<b>pullik yuklash</b> ({price} so'm) sotib olishi kerak.\n"
        f"🔗 <b>Sizning havolangiz:</b>\n<code>{ref_link}</code>"
    )


def referrer_reward_message(ref_info: dict[str, Any]) -> str:
    if ref_info.get("rewarded"):
        added = int(ref_info.get("credits_added") or 1)
        return (
            "🎉 <b>Tabriklaymiz!</b>\n\n"
            "Referral dasturi bo'yicha shartlar to'liq bajarildi: "
            "3 ta do'stingiz hujjat yuklab oldi va ulardan kamida bittasi pullik xarid qildi.\n\n"
            f"Sizga <b>+{added} ta bepul yuklash</b> taqdim etildi! 💳"
        )

    batch_progress = int(ref_info.get("batch_progress") or 0)
    batch_has_paid = bool(ref_info.get("batch_has_paid"))
    if batch_has_paid:
        need = max(0, 3 - batch_progress)
        return (
            "👥 <b>Yangi faol taklif!</b>\n\n"
            f"Do'stingiz birinchi hujjatini yuklab oldi. "
            f"Joriy bosqich: <b>{batch_progress}/3</b>.\n"
            f"Yana <b>{need} ta</b> do'st hujjat yuklab olsa, shart bajariladi "
            "(pullik xarid allaqachon bor ✅)."
        )

    return (
        "👥 <b>Yangi faol taklif!</b>\n\n"
        f"Do'stingiz birinchi hujjatini yuklab oldi. "
        f"Joriy bosqich: <b>{batch_progress}/3</b>.\n\n"
        "ℹ️ Eslatma: 3 ta do'st yuklab olgach, ulardan <b>kamida 1 nafari</b> "
        "pullik yuklash sotib olishi kerak — shundan keyin sizga +1 bepul yuklash beriladi."
    )


def referrer_paid_progress_message(ref_info: dict[str, Any]) -> str:
    if ref_info.get("rewarded"):
        return referrer_reward_message(ref_info)

    batch_progress = int(ref_info.get("batch_progress") or 0)
    batch_has_paid = bool(ref_info.get("batch_has_paid"))
    if batch_has_paid and batch_progress < 3:
        need = max(0, 3 - batch_progress)
        return (
            "💳 <b>Taklif qilgan do'stingiz to'lov qildi!</b>\n\n"
            f"Joriy bosqich: <b>{batch_progress}/3</b> (pullik xarid ✅).\n"
            f"Yana <b>{need} ta</b> do'st hujjat yuklab olsa, sizga +1 bepul yuklash beriladi."
        )
    if batch_has_paid:
        return referrer_reward_message(ref_info)

    return (
        "💳 <b>Taklif qilgan do'stingiz to'lov qildi!</b>\n\n"
        f"Joriy bosqich: <b>{batch_progress}/3</b>.\n"
        "3 ta do'st hujjat yuklab olgach, ulardan kamida bittasi pullik xarid qilgani "
        "uchun mukofot faollashadi."
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
