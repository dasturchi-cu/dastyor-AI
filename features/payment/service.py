"""Manual payment flow with credit grants."""
from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Any

from config.settings import RECEIPTS_DIR, settings
from database.repositories import payments as payments_repo
from database.repositories import users as users_repo

logger = logging.getLogger(__name__)


def payment_info() -> dict[str, Any]:
    from shared.pricing import list_packages

    return {
        "card_number": settings.payment_card_number,
        "card_owner": settings.payment_card_owner,
        "single_doc_price_uzs": settings.single_doc_price_uzs,
        "packages": list_packages(),
        "pay_promo_hours": int(getattr(settings, "pay_promo_hours", 24) or 24),
        "credit_note": (
            "Demo (belgili) bepul. Toza fayl — paket: "
            "1× / 3× / 5×. Bugun to'lasangiz +1 muqova bonus."
        ),
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
        package_id="pack3",
    )
    if not payment:
        raise RuntimeError("To'lov saqlanmadi")
    return payment


def approve_payment(
    payment_id: int,
    admin_note: str | None = None,
    *,
    approved_by: int | None = None,
) -> dict[str, Any] | None:
    result = payments_repo.approve_atomic(
        payment_id, admin_note, approved_by=approved_by
    )
    if result and result.get("telegram_id"):
        ref_info = users_repo.mark_referral_paid(int(result["telegram_id"]))
        if ref_info:
            result["referral_info"] = ref_info
    return result


def try_auto_approve(payment_id: int) -> dict[str, Any] | None:
    """Skrinshot kelgach avtomatik tasdiqlash (AUTO_APPROVE_PAYMENTS=1)."""
    if not settings.auto_approve_payments:
        return None
    return approve_payment(payment_id, admin_note="verified")


def reject_payment(payment_id: int, admin_note: str | None = None) -> bool:
    return payments_repo.set_status(payment_id, "REJECTED", admin_note)


def list_pending() -> list[dict[str, Any]]:
    return payments_repo.list_payments("PENDING")


async def create_checkout_uz_payment(
    telegram_id: int, package_id: str, document_type: str
) -> dict[str, Any]:
    """Create a checkout.uz payment link for a package purchase.

    Raises core.checkout_uz.CheckoutUzError on any failure (misconfiguration,
    network error, bad gateway response) so the caller can show the user a
    clear message instead of leaving them waiting.
    """
    from core import checkout_uz
    from shared.pricing import get_package

    if not settings.checkout_uz_webhook_url:
        raise checkout_uz.CheckoutUzError(
            "Webhook manzili sozlanmagan (SITE_BASE_URL yoki WEBHOOK_URL kerak)"
        )

    pack = get_package(package_id)
    description = f"DASTYOR AI — {pack.label} ({pack.credits} ta hujjat)"
    gw_payment = await checkout_uz.create_payment(
        pack.price_uzs, description, settings.checkout_uz_webhook_url
    )

    payment = payments_repo.create_payment(
        telegram_id,
        payer_name="checkout.uz",
        document_type=document_type,
        package_id=package_id,
        gateway="checkout_uz",
    )
    if not payment:
        raise checkout_uz.CheckoutUzError("To'lov yozuvi saqlanmadi")

    payments_repo.set_gateway_info(
        int(payment["id"]),
        gateway_payment_id=str(gw_payment.get("_id")),
        gateway_uuid=str(gw_payment.get("_uuid") or ""),
        gateway_payment_url=str(gw_payment.get("_url")),
    )
    return payments_repo.get_payment(int(payment["id"])) or payment


async def confirm_checkout_uz_payment(gateway_payment_id: str, bot: Any = None) -> None:
    """Handle a checkout.uz webhook notification for one gateway payment id.

    SECURITY: the webhook body itself is never trusted for the paid/amount
    decision — we re-fetch status from checkout.uz with our own API key and
    only credit the user if that call itself says "paid" with a matching
    amount. approve_atomic() makes crediting idempotent, so a duplicate
    webhook delivery never double-credits.
    """
    from core import checkout_uz

    payment = payments_repo.get_by_gateway_payment_id(gateway_payment_id)
    if not payment:
        logger.warning(
            "checkout.uz webhook: no local payment for gateway_payment_id=%s", gateway_payment_id
        )
        return

    pid_for_lookup: int | str = (
        int(gateway_payment_id) if gateway_payment_id.isdigit() else gateway_payment_id
    )
    status_data = await checkout_uz.check_status(payment_id=pid_for_lookup)
    if not status_data:
        logger.warning(
            "checkout.uz webhook: status_payment unavailable for id=%s", gateway_payment_id
        )
        return

    paid = str(status_data.get("status") or "").strip().lower() == "paid"
    remote_amount = int(status_data.get("amount") or 0)
    local_amount = int(payment.get("amount") or 0)
    if not paid or remote_amount != local_amount:
        logger.info(
            "checkout.uz webhook: not confirmed (paid=%s remote_amount=%s local_amount=%s) id=%s",
            paid,
            remote_amount,
            local_amount,
            gateway_payment_id,
        )
        return

    result = approve_payment(int(payment["id"]))
    if not result or result.get("already_approved"):
        return

    telegram_id = int(payment.get("telegram_id") or 0)
    if not telegram_id or not bot:
        return
    from features.payment.router import _notify_user_payment_approved

    await _notify_user_payment_approved(
        bot,
        telegram_id,
        int(result.get("credits_granted") or 0),
        result.get("document_type"),
        promo_bonus=int(result.get("promo_bonus_granted") or 0),
    )
