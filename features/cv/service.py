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


async def export_pdf(telegram_id: int, payload: dict[str, Any]) -> tuple[bytes, str]:
    if not await async_db.run(users_repo.consume_credit, telegram_id):
        raise PermissionError("Kredit yetarli emas. To'lov qiling.")

    try:
        pdf = await generate_cv_pdf(payload, base_url=settings.site_base_url or settings.webapp_base)
        if not pdf:
            await async_db.run(users_repo.add_credits, telegram_id, 1)
            raise RuntimeError("PDF yaratib bo'lmadi")
        return await async_db.run(_export_pdf_sync, telegram_id, payload, pdf)
    except Exception:
        await async_db.run(users_repo.add_credits, telegram_id, 1)
        raise


def preview(payload: dict[str, Any]) -> str:
    return preview_html(payload)
