"""Test / smoke / audit akkauntlar — admin ko'rinishidan yashiriladi."""
from __future__ import annotations

from typing import Any

from config.settings import settings

_BUILTIN_TEST_TELEGRAM_IDS = frozenset(
    {88001122, 88003344, 88005566, 88007788, 990001234, 999888777, 123456789}
)

_TEST_NAME_MARKERS = (
    "manual user",
    "auto user",
    "smoke test",
    "smoke user",
    "audit payer",
    "audit test",
    "audit user",
    "test user",
)

_TEST_EXACT_NAMES = frozenset({"test", "smoke", "audit test"})

_TEST_USERNAMES = frozenset({"smoke", "audit_user", "audit", "test", "smoke_test"})


def _test_telegram_ids() -> frozenset[int]:
    return frozenset(settings.payment_test_telegram_ids) | _BUILTIN_TEST_TELEGRAM_IDS


def _account_is_test(
    *,
    telegram_id: Any = None,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    payer_name: str | None = None,
) -> bool:
    try:
        tid = int(telegram_id or 0)
    except (TypeError, ValueError):
        tid = 0
    if tid and tid in _test_telegram_ids():
        return True

    first = str(first_name or "").strip().lower()
    last = str(last_name or "").strip().lower()
    combined = f"{first} {last}".strip()
    payer = str(payer_name or "").strip().lower()
    blob = combined if combined and combined != "—" else payer
    if blob in _TEST_EXACT_NAMES:
        return True
    if any(marker in blob for marker in _TEST_NAME_MARKERS):
        return True

    uname = str(username or "").strip().lstrip("@").lower()
    if uname in _TEST_USERNAMES:
        return True
    return False


def is_test_user(user: dict[str, Any] | None) -> bool:
    if not user:
        return False
    return _account_is_test(
        telegram_id=user.get("telegram_id"),
        username=user.get("username"),
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
    )


def filter_real_users(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if not is_test_user(row)]


def is_test_payment(payment: dict[str, Any] | None) -> bool:
    if not payment:
        return False
    from shared.payment_notifications import full_name_from_payment

    payer = str(payment.get("payer_name") or "").strip()
    if not payer or payer == "—":
        payer = full_name_from_payment(payment)
    return _account_is_test(
        telegram_id=payment.get("telegram_id"),
        username=payment.get("username"),
        first_name=payment.get("first_name"),
        last_name=payment.get("last_name"),
        payer_name=payer,
    )
