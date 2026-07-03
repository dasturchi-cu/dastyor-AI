"""CV business logic."""
from __future__ import annotations

import time
from typing import Any

from config.settings import GENERATED_DIR, settings
from database.repositories import cv_data as cv_repo
from database.repositories import generated_files as files_repo
from database.repositories import users as users_repo
from features.cv.render import generate_cv_pdf, preview_html
from shared import async_db


def save_user_data(telegram_id: int, payload: dict[str, Any]) -> None:
    cv_repo.save(telegram_id, payload)


def get_saved_data(telegram_id: int) -> dict[str, Any] | None:
    return cv_repo.get(telegram_id)


def _export_pdf_sync(telegram_id: int, payload: dict[str, Any], pdf: bytes) -> tuple[bytes, str]:
    cv_repo.save(telegram_id, payload)
    safe = (payload.get("name") or "CV").replace(" ", "_")[:30]
    ts = int(time.time())
    filename = f"DASTYOR_CV_{safe}_{ts}.pdf"
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = GENERATED_DIR / f"{telegram_id}_{ts}_cv.pdf"
    out_path.write_bytes(pdf)
    files_repo.record_file(telegram_id, "cv", str(out_path), filename)
    return pdf, filename


async def export_pdf(telegram_id: int, payload: dict[str, Any], bot: Any | None = None) -> tuple[bytes, str]:
    if not await async_db.run(users_repo.consume_credit, telegram_id):
        raise PermissionError("Pul yetarli emas. Avval to'lov qiling.")

    try:
        pdf = await generate_cv_pdf(payload, base_url=settings.site_base_url or settings.webapp_base)
        if not pdf:
            await async_db.run(users_repo.add_credits, telegram_id, 1)
            raise RuntimeError("PDF yaratib bo'lmadi")
        res = await async_db.run(_export_pdf_sync, telegram_id, payload, pdf)

        # Activate referral
        ref_info = await async_db.run(users_repo.activate_referral, telegram_id)
        if ref_info and bot:
            ref_id = ref_info["referrer_id"]
            active_count = ref_info["active_count"]
            rewarded = ref_info["rewarded"]
            try:
                if rewarded:
                    await bot.send_message(
                        chat_id=ref_id,
                        text=f"🎉 <b>Tabriklaymiz!</b> Taklifnomangiz orqali 3 ta do'stingiz (jami {active_count} ta) "
                             f"o'zining birinchi bepul hujjatini yuklab oldi.\n\n"
                             f"Sizga <b>+1 ta bepul yuklash limiti</b> berildi! 💳"
                    )
                else:
                    needed = 3 - (active_count % 3)
                    await bot.send_message(
                        chat_id=ref_id,
                        text=f"👥 <b>Yangi faol taklif!</b> Do'stingiz o'zining birinchi bepul hujjatini yuklab oldi.\n\n"
                             f"Hozirda faol takliflaringiz: <b>{active_count} ta</b>.\n"
                             f"Yana <b>{needed} ta</b> do'stingiz yuklab olsa, sizga +1 bepul yuklash limiti sovg'a qilinadi! 🎁"
                    )
            except Exception:
                pass

        return res
    except Exception:
        await async_db.run(users_repo.add_credits, telegram_id, 1)
        raise


def preview(payload: dict[str, Any]) -> str:
    return preview_html(payload)
