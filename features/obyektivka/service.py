"""Obyektivka DOCX — master template placeholder replace (reference clone)."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from backend.services.document_render.photo import compress_payload_photo
from features.obyektivka.docx_template import generate_obyektivka_docx
from config.settings import GENERATED_DIR
from database.repositories import generated_files as files_repo
from database.repositories import obyektivka_data as oby_repo
from database.repositories import users as users_repo
from shared import async_db


def _prepare_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return compress_payload_photo(dict(payload or {}))


def save_user_data(telegram_id: int, payload: dict[str, Any]) -> None:
    oby_repo.save_payload(telegram_id, _prepare_payload(payload))


def get_saved_data(telegram_id: int) -> dict[str, Any] | None:
    return oby_repo.get_payload(telegram_id)


def get_pending(telegram_id: int) -> dict[str, Any] | None:
    return oby_repo.get_pending(telegram_id)


def save_pending(telegram_id: int, payload: dict[str, Any]) -> None:
    oby_repo.save_pending(telegram_id, _prepare_payload(payload))


def _export_docx_sync(telegram_id: int, payload: dict[str, Any]) -> tuple[bytes, str]:
    clean = _prepare_payload(payload)
    path = generate_obyektivka_docx(clean)
    if not path or not Path(path).is_file():
        raise RuntimeError("DOCX yaratib bo'lmadi")

    docx_bytes = Path(path).read_bytes()
    Path(path).unlink(missing_ok=True)
    oby_repo.save_payload(telegram_id, clean)

    fn = (clean.get("fullname") or "Obyektivka").replace(" ", "_")[:30]
    ts = int(time.time())
    filename = f"DASTYOR_OBY_{fn}_{ts}.docx"

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = GENERATED_DIR / f"{telegram_id}_{ts}_oby.docx"
    out_path.write_bytes(docx_bytes)
    files_repo.record_file(telegram_id, "obyektivka", str(out_path), filename)
    return docx_bytes, filename


async def export_docx(telegram_id: int, payload: dict[str, Any], bot: Any | None = None) -> tuple[bytes, str]:
    if not await async_db.run(users_repo.consume_credit, telegram_id):
        raise PermissionError("Pul yetarli emas. Avval to'lov qiling.")

    try:
        res = await async_db.run(_export_docx_sync, telegram_id, payload)

        # Activate referral
        ref_info = await async_db.run(users_repo.activate_referral, telegram_id)
        if ref_info and bot:
            from shared.referral import notify_referrer

            await notify_referrer(bot, ref_info, event="download")

        return res
    except Exception:
        await async_db.run(users_repo.add_credits, telegram_id, 1)
        raise
