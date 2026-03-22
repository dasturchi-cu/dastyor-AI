"""
Tarif bo'yicha xizmat limitlari (premium.html kartalariga mos).
Kunlik / oylik / obuna davri bo'yicha bucket hisoblanadi.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

LOCAL_BUCKETS_FILE = "service_usage_buckets.json"

# Kategoriya kalitlari (record_service_completion va tekshiruvlar bilan bir xil)
CAT_TRANSLIT = "translit"
CAT_IMAGE_PDF = "image_pdf"
CAT_TRANSLATE = "translate"
CAT_OBYEKTIVKA = "obyektivka"
CAT_CV = "cv"
CAT_OCR = "ocr"
CAT_SPELL = "spell"
CAT_TRANSCRIBE = "transcribe"  # ovoz → matn (kartada alohida yo'q — OCR bilan bir xil limit)

# (mode, cap) — mode: unlimited | day | month | subscription | blocked
# blocked: cap 0 — xizmat yo'q
_LIMITS: dict[str, dict[str, tuple[str, int | None]]] = {
    "free": {
        CAT_TRANSLIT: ("day", 5),
        CAT_IMAGE_PDF: ("day", 5),
        CAT_TRANSLATE: ("day", 1),
        CAT_OBYEKTIVKA: ("blocked", 0),
        CAT_CV: ("blocked", 0),
        CAT_OCR: ("blocked", 0),
        CAT_SPELL: ("blocked", 0),
        CAT_TRANSCRIBE: ("blocked", 0),
    },
    "standard": {
        CAT_TRANSLIT: ("unlimited", None),
        CAT_IMAGE_PDF: ("unlimited", None),
        CAT_TRANSLATE: ("day", 10),
        CAT_OBYEKTIVKA: ("subscription", 1),
        CAT_CV: ("subscription", 1),
        CAT_OCR: ("day", 5),
        CAT_SPELL: ("day", 5),
        CAT_TRANSCRIBE: ("day", 5),
    },
    "premium": {
        CAT_TRANSLIT: ("unlimited", None),
        CAT_IMAGE_PDF: ("unlimited", None),
        CAT_TRANSLATE: ("unlimited", None),
        CAT_SPELL: ("unlimited", None),
        CAT_OBYEKTIVKA: ("month", 6),
        CAT_CV: ("month", 6),
        CAT_OCR: ("day", 10),
        CAT_TRANSCRIBE: ("unlimited", None),
    },
}

_CATEGORY_LABELS_UZ: dict[str, str] = {
    CAT_TRANSLIT: "Krill ↔ Lotin",
    CAT_IMAGE_PDF: "Rasm → PDF",
    CAT_TRANSLATE: "Tarjima",
    CAT_OBYEKTIVKA: "Obyektivka",
    CAT_CV: "CV / Rezyume",
    CAT_OCR: "AI skayner (OCR)",
    CAT_SPELL: "Imlo tekshirish",
    CAT_TRANSCRIBE: "Ovoz → matn",
}

_ORDER = [
    CAT_TRANSLIT,
    CAT_IMAGE_PDF,
    CAT_TRANSLATE,
    CAT_OBYEKTIVKA,
    CAT_CV,
    CAT_OCR,
    CAT_SPELL,
    CAT_TRANSCRIBE,
]


def category_label_uz(cat: str) -> str:
    return _CATEGORY_LABELS_UZ.get(cat, cat)


def _plan_limits(plan: str) -> dict[str, tuple[str, int | None]]:
    return _LIMITS.get(plan, _LIMITS["free"])


def _subscription_row_for_buckets(user_id: int) -> Optional[dict]:
    try:
        from bot.services.supabase_db import db_pick_active_subscription_row

        return db_pick_active_subscription_row(int(user_id))
    except Exception as e:
        logger.debug("plan_limits subscription row: %s", e)
        return None


def resolve_bucket_key(user_id: int, category: str, mode: str) -> Optional[str]:
    """
    None = cheksiz yoki blocked (hisob yo'q).
    """
    if mode in ("unlimited", "blocked"):
        return None
    uid = int(user_id)
    if mode == "day":
        return f"d:{date.today().isoformat()}:{category}"
    if mode == "month":
        return f"m:{date.today().strftime('%Y-%m')}:{category}"
    if mode == "subscription":
        row = _subscription_row_for_buckets(uid)
        if not row:
            return None
        sid = row.get("id")
        if sid is None:
            return None
        return f"s:{sid}:{category}"
    return None


def _get_bucket_count(user_id: int, bucket_key: str) -> int:
    uid = int(user_id)
    try:
        from bot.services.supabase_db import has_db, db_service_bucket_get

        if has_db():
            return int(db_service_bucket_get(uid, bucket_key))
    except Exception as e:
        logger.debug("plan_limits db get: %s", e)
    return _local_bucket_get(uid, bucket_key)


def _local_bucket_get(user_id: int, bucket_key: str) -> int:
    try:
        if not os.path.exists(LOCAL_BUCKETS_FILE):
            return 0
        with open(LOCAL_BUCKETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return int(data.get(f"{user_id}|{bucket_key}", 0))
    except Exception:
        return 0


def _local_bucket_incr(user_id: int, bucket_key: str) -> int:
    data: dict[str, Any] = {}
    try:
        if os.path.exists(LOCAL_BUCKETS_FILE):
            with open(LOCAL_BUCKETS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
    except Exception:
        data = {}
    k = f"{user_id}|{bucket_key}"
    data[k] = int(data.get(k, 0)) + 1
    try:
        with open(LOCAL_BUCKETS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=0)
    except Exception as e:
        logger.error("plan_limits local save: %s", e)
    return int(data[k])


def _incr_bucket(user_id: int, bucket_key: str) -> int:
    uid = int(user_id)
    try:
        from bot.services.supabase_db import has_db, db_service_bucket_increment

        if has_db():
            return int(db_service_bucket_increment(uid, bucket_key))
    except Exception as e:
        logger.debug("plan_limits db incr: %s", e)
    return _local_bucket_incr(uid, bucket_key)


def category_status(user_id: int, category: str) -> dict[str, Any]:
    """Bitta kategoriya: used, limit, remaining, unlimited, blocked, label, period_note."""
    from bot.services.settings_service import get_active_plan_code

    uid = int(user_id)
    plan = get_active_plan_code(uid)
    mode, cap = _plan_limits(plan).get(category, ("blocked", 0))
    label = category_label_uz(category)

    if mode == "unlimited":
        return {
            "category": category,
            "label": label,
            "unlimited": True,
            "blocked": False,
            "used": None,
            "limit": None,
            "remaining": None,
            "period_note": "cheksiz",
        }
    if mode == "blocked" or cap == 0:
        return {
            "category": category,
            "label": label,
            "unlimited": False,
            "blocked": True,
            "used": 0,
            "limit": 0,
            "remaining": 0,
            "period_note": "mavjud emas",
        }

    bkey = resolve_bucket_key(uid, category, mode)
    if not bkey:
        return {
            "category": category,
            "label": label,
            "unlimited": False,
            "blocked": True,
            "used": 0,
            "limit": int(cap or 0),
            "remaining": 0,
            "period_note": "obuna topilmadi",
        }

    used = _get_bucket_count(uid, bkey)
    lim = int(cap or 0)
    rem = max(0, lim - used)
    if mode == "day":
        pnote = "kunlik"
    elif mode == "month":
        pnote = "oylik"
    else:
        pnote = "obuna davri"

    return {
        "category": category,
        "label": label,
        "unlimited": False,
        "blocked": False,
        "used": used,
        "limit": lim,
        "remaining": rem,
        "period_note": pnote,
    }


def can_use_category(user_id: int, category: str) -> bool:
    from bot.services.admin_service import is_admin

    if is_admin(int(user_id)):
        return True
    st = category_status(user_id, category)
    if st.get("unlimited"):
        return True
    if st.get("blocked"):
        return False
    rem = st.get("remaining")
    return rem is not None and int(rem) > 0


def record_category_use(user_id: int, category: str) -> bool:
    """
    Muvaffaqiyatli xizmatdan keyin chaqiriladi.
    False = cheksiz/blocked yoki bucket yo'q (increment qilinmadi).
    """
    from bot.services.admin_service import is_admin

    uid = int(user_id)
    if is_admin(uid):
        return True
    st = category_status(uid, category)
    if st.get("unlimited"):
        return True
    if st.get("blocked"):
        return False
    from bot.services.settings_service import get_active_plan_code

    plan = get_active_plan_code(uid)
    mode, cap = _plan_limits(plan).get(category, ("blocked", 0))
    if mode in ("unlimited", "blocked"):
        return mode == "unlimited"
    bkey = resolve_bucket_key(uid, category, mode)
    if not bkey:
        return False
    _incr_bucket(uid, bkey)
    try:
        from bot.services.supabase_db import db_log_usage

        db_log_usage(uid, f"quota:{category}", {"bucket": bkey})
    except Exception:
        pass
    return True


def user_limits_breakdown(user_id: int) -> list[dict[str, Any]]:
    """API / balans uchun barcha kategoriyalar ro'yxati."""
    out: list[dict[str, Any]] = []
    for cat in _ORDER:
        st = category_status(user_id, cat)
        line = {
            "category": cat,
            "label": st["label"],
            "unlimited": st["unlimited"],
            "blocked": st["blocked"],
            "used": st.get("used"),
            "limit": st.get("limit"),
            "remaining": st.get("remaining"),
            "period": st.get("period_note"),
        }
        if st["unlimited"]:
            line["display"] = f"{st['label']}: ♾ cheksiz"
        elif st["blocked"]:
            line["display"] = f"{st['label']}: — (tarifda yo'q)"
        else:
            u = st.get("used", 0)
            l = st.get("limit", 0)
            r = st.get("remaining", 0)
            pn = st.get("period_note", "")
            line["display"] = (
                f"{st['label']}: ishlatilgan {u}, limit {l} ({pn}), qoldi {r}"
            )
        out.append(line)
    return out


def block_reason_for_user_uz(user_id: int, category: str) -> str:
    uid = int(user_id)
    if can_use_category(uid, category):
        return ""
    st = category_status(uid, category)
    if st.get("blocked"):
        return f"❌ «{st['label']}» hozirgi tarifda yo'q. Standard yoki Premium oling."
    if st.get("unlimited"):
        return ""
    return (
        f"⛔️ «{st['label']}» limiti tugadi ({st.get('period_note', '')}). "
        f"Berilgan: {st.get('used', 0)}/{st.get('limit', 0)}. "
        "Tarifni yangilang yoki keyingi davrni kuting."
    )
