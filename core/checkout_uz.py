"""checkout.uz payment gateway client (Click/Payme/Uzcard/Humo/Plum).

SECURITY: checkout.uz webhook requests carry no signature. Callers must
never trust a webhook body directly — always re-fetch status via
check_status() with our own API key before crediting anything.
See features/payment/service.confirm_checkout_uz_payment().
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0


class CheckoutUzError(Exception):
    """Raised when a checkout.uz API call fails or returns an error status."""


def is_configured() -> bool:
    return bool((settings.checkout_uz_api_key or "").strip())


def _base_url() -> str:
    return (settings.checkout_uz_base_url or "https://checkout.uz/api/v1").rstrip("/")


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {(settings.checkout_uz_api_key or '').strip()}"}


async def create_payment(amount: int, description: str, webhook_url: str) -> dict[str, Any]:
    """POST /create_payment. Returns the "payment" object (_id, _uuid, _url).

    Raises CheckoutUzError on any failure — callers must not silently swallow this,
    since the customer needs a clear message instead of a hang.
    """
    if not is_configured():
        raise CheckoutUzError("CHECKOUT_UZ_API_KEY sozlanmagan")

    payload = {
        "amount": int(amount),
        "description": description,
        "webhook_url": webhook_url,
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{_base_url()}/create_payment", json=payload, headers=_headers()
            )
            data = resp.json()
    except Exception as exc:
        logger.warning("checkout.uz create_payment request failed: %s", exc)
        raise CheckoutUzError("checkout.uz bilan bog'lanib bo'lmadi") from exc

    if resp.status_code >= 400 or data.get("status") != "success":
        logger.warning(
            "checkout.uz create_payment error: status=%s body=%s", resp.status_code, data
        )
        raise CheckoutUzError(str(data.get("message") or "checkout.uz to'lov yaratolmadi"))

    payment = data.get("payment") or {}
    if not payment.get("_url"):
        raise CheckoutUzError("checkout.uz javobida to'lov havolasi topilmadi")
    return payment


async def check_status(
    *, payment_id: int | str | None = None, uuid: str | None = None
) -> dict[str, Any] | None:
    """POST /status_payment. Returns the "data" object, or None on any failure/misconfig.

    Never raises — this is used from the webhook path, which must always respond
    quickly; callers treat None as "could not verify, do not credit anything".
    """
    if not is_configured() or (not payment_id and not uuid):
        return None

    body: dict[str, Any] = {}
    if payment_id is not None:
        body["id"] = payment_id
    if uuid:
        body["uuid"] = uuid

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{_base_url()}/status_payment", json=body, headers=_headers()
            )
            data = resp.json()
    except Exception as exc:
        logger.warning("checkout.uz status_payment request failed: %s", exc)
        return None

    if resp.status_code >= 400 or data.get("status") != "success":
        logger.warning(
            "checkout.uz status_payment error: status=%s body=%s", resp.status_code, data
        )
        return None

    return data.get("data") or {}
