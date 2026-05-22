"""Veb profil va CV/obyektivka eksport: bir martalik 5 000 so'm."""
from __future__ import annotations

from fastapi import HTTPException


def build_web_me_quota_fields(uid: int) -> dict:
    from bot.services.settings_service import get_active_plan_code
    from bot.services.plan_limits import user_limits_breakdown
    from bot.services.supabase_db import (
        db_user_has_cv_access,
        db_user_has_objective_access,
        has_db,
    )

    u = int(uid)
    plan = get_active_plan_code(u)
    has_cv = False
    has_obj = False
    if has_db():
        try:
            from bot.services.supabase_db import db_get_user
            from bot.services.plan_limits import _paid_access_flags_from_row

            row = db_get_user(u)
            has_cv, has_obj = _paid_access_flags_from_row(row)
        except Exception:
            has_cv = bool(db_user_has_cv_access(u))
            has_obj = bool(db_user_has_objective_access(u))
    plan_labels = {
        "free": "Bepul",
        "standard": "Standard",
        "premium": "Premium",
    }
    return {
        "plan": plan,
        "user_plan": plan,
        "plan_label": plan_labels.get(plan, plan),
        "has_cv_access": has_cv,
        "has_objective_access": has_obj,
        "limits_breakdown": user_limits_breakdown(u, plan),
    }


def _paid_once_bucket_used(uid: int, category: str) -> bool:
    from bot.services.plan_limits import CAT_CV, CAT_OBYEKTIVKA, _get_bucket_count

    u = int(uid)
    cat = (category or "").strip().lower()
    if cat == CAT_CV:
        return _get_bucket_count(u, f"paid_once:{CAT_CV}:{u}") >= 1
    if cat == CAT_OBYEKTIVKA:
        return _get_bucket_count(u, f"paid_once:{CAT_OBYEKTIVKA}:{u}") >= 1
    return False


def require_paid_single_doc_or_subscription(uid: int, category: str) -> None:
    """
    Free: faqat admin tasdiqlagan bir martalik to'lov (has_*_access).
    Standard/Premium: obuna limiti (web_quota_consume_or_raise).
    """
    from bot.services.admin_service import is_admin
    from bot.services.plan_limits import CAT_CV, CAT_OBYEKTIVKA
    from bot.services.settings_service import get_active_plan_code
    from bot.services.supabase_db import (
        db_user_has_cv_access,
        db_user_has_objective_access,
        has_db,
    )

    u = int(uid)
    if is_admin(u):
        return
    cat = (category or "").strip().lower()
    if cat not in (CAT_CV, CAT_OBYEKTIVKA):
        return
    plan = get_active_plan_code(u)
    if plan in ("standard", "premium"):
        return
    if has_db() and _paid_once_bucket_used(u, cat):
        label = "CV" if cat == CAT_CV else "Obyektivka"
        raise HTTPException(
            status_code=402,
            detail=f"❌ «{label}» to'lovi ishlatilgan. Yangi to'lov kerak.",
        )
    if cat == CAT_CV and has_db() and db_user_has_cv_access(u):
        return
    if cat == CAT_OBYEKTIVKA and has_db() and db_user_has_objective_access(u):
        return
    try:
        from bot.services.pricing import SINGLE_DOC_PRICE_UZS

        price = int(SINGLE_DOC_PRICE_UZS)
    except Exception:
        price = 5000
    label = "CV" if cat == CAT_CV else "Obyektivka"
    raise HTTPException(
        status_code=402,
        detail=f"❌ «{label}» — avval {price} so'm to'lov (skrinshot).",
    )
