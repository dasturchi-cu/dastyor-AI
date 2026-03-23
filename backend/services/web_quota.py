"""Veb API: tarif limiti (bot bilan bir xil kategoriyalar)."""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException


def web_quota_consume_or_raise(uid: int, category: str) -> bool:
    """
    Oldindan bitta limit yeb olish (CV / obyektivka eksport — parallel so‘rovlarda ishonchli).

    Admin: False qaytadi (limit completion / record_service_completion da yoziladi).

    Returns:
        True — completion da record_service_completion(..., skip_quota=True)
        False — admin; completion da oddiy record_service_completion
    """
    from bot.services.admin_service import is_admin
    from bot.services.plan_limits import block_reason_for_user_uz, record_category_use

    u = int(uid)
    if is_admin(u):
        return False
    if not record_category_use(u, category):
        raise HTTPException(
            status_code=429,
            detail=block_reason_for_user_uz(u, category) or "Bu xizmat pullik. Standard yoki Premium tarifni oling.",
        )
    return True


def web_quota_commit_success(uid: int, category: str, service_label: str) -> dict[str, Any]:
    """
    Muvaffaqiyatli xizmatdan keyin atomik +1 (OCR, tarjima, imlo, rasm→PDF, …).
    Limit bo‘lmasa 429 — oldingi `can_use` + keyinroq `record` oralig‘idagi pauzalar yo‘q.
    """
    from bot.services.plan_limits import block_reason_for_user_uz, category_quota_for_response, record_category_use
    from bot.services.user_service import record_service_completion

    u = int(uid)
    if not record_category_use(u, category):
        raise HTTPException(
            status_code=429,
            detail=block_reason_for_user_uz(u, category) or "Bu xizmat pullik. Standard yoki Premium tarifni oling.",
        )
    record_service_completion(u, category, service_label, skip_quota=True)
    return category_quota_for_response(u, category)
