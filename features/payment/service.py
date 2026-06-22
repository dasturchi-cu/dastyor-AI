"""Manual payment flow with credit grants."""
from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from config.settings import RECEIPTS_DIR, settings
from database.repositories import payments as payments_repo
from database.repositories import users as users_repo


def payment_info() -> dict[str, Any]:
    return {
        "card_number": settings.payment_card_number,
        "card_owner": settings.payment_card_owner,
        "single_doc_price_uzs": settings.single_doc_price_uzs,
    }


def user_status(telegram_id: int) -> dict[str, Any]:
    user = users_repo.upsert_user(telegram_id)
    return {
        "credits": int(user.get("credits") or 0),
        "telegram_id": telegram_id,
        "pending_payments": payments_repo.count_user_pending(telegram_id),
    }


def submit_payment(
    telegram_id: int,
    payer_name: str,
    card_number: str,
    receipt_bytes: bytes,
    filename: str,
) -> dict[str, Any]:
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(filename).suffix.lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"
    safe_name = f"{telegram_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}{ext}"
    receipt_path = RECEIPTS_DIR / safe_name
    receipt_path.write_bytes(receipt_bytes)

    payment = payments_repo.create_payment(
        telegram_id,
        payer_name=payer_name,
        card_number=card_number,
        receipt_path=str(receipt_path),
        document_type="manual",
    )
    if not payment:
        raise RuntimeError("To'lov saqlanmadi")
    return payment


def approve_payment(payment_id: int, admin_note: str | None = None) -> dict[str, Any] | None:
    return payments_repo.approve_atomic(payment_id, admin_note)


def try_auto_approve(payment_id: int) -> dict[str, Any] | None:
    """Skrinshot kelgach avtomatik tasdiqlash (AUTO_APPROVE_PAYMENTS=1)."""
    if not settings.auto_approve_payments:
        return None
    return approve_payment(payment_id, admin_note="auto")


def reject_payment(payment_id: int, admin_note: str | None = None) -> bool:
    return payments_repo.set_status(payment_id, "REJECTED", admin_note)


def list_pending() -> list[dict[str, Any]]:
    return payments_repo.list_payments("PENDING")
