"""Veb API: tarif limiti (bot bilan bir xil kategoriyalar)."""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException


def web_quota_before(uid: int, category: str) -> None:
    from bot.services.plan_limits import block_reason_for_user_uz, can_use_category

    u = int(uid)
    if not can_use_category(u, category):
        raise HTTPException(
            status_code=429,
            detail=block_reason_for_user_uz(u, category) or "Limit tugadi. Tarifni yangilang.",
        )


def web_quota_after(uid: int, category: str, service_label: str) -> dict[str, Any]:
    from bot.services.plan_limits import category_quota_for_response
    from bot.services.user_service import record_service_completion

    record_service_completion(int(uid), category, service_label)
    return category_quota_for_response(int(uid), category)
