"""Test / smoke / audit to'lovlari — admin kanaliga yuborilmasin."""
from __future__ import annotations

from typing import Any

from config.settings import settings
from shared.payment_notifications import full_name_from_payment

_BUILTIN_TEST_TELEGRAM_IDS = frozenset({88005566, 999888777})

_TEST_NAME_MARKERS = (
    "manual user",
    "smoke test",
    "smoke user",
    "audit payer",
    "audit test",
    "audit user",
    "test user",
)

_TEST_USERNAMES = frozenset({"smoke", "audit_user", "audit", "test", "smoke_test"})


def _test_telegram_ids() -> frozenset[int]:
    return frozenset(settings.payment_test_telegram_ids) | _BUILTIN_TEST_TELEGRAM_IDS


def is_test_payment(payment: dict[str, Any] | None) -> bool:
    if not payment:
        return False
    try:
        tid = int(payment.get("telegram_id") or 0)
    except (TypeError, ValueError):
        tid = 0
    if tid and tid in _test_telegram_ids():
        return True

    name = full_name_from_payment(payment).lower()
    payer = str(payment.get("payer_name") or "").strip().lower()
    blob = f"{name} {payer}"
    if any(marker in blob for marker in _TEST_NAME_MARKERS):
        return True

    username = str(payment.get("username") or "").strip().lstrip("@").lower()
    if username in _TEST_USERNAMES:
        return True
    return False
