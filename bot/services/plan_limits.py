"""
Tarif bo'yicha xizmat limitlari (premium.html kartalariga mos).
Kunlik / oylik / obuna davri bo'yicha bucket hisoblanadi.

Barcha kategoriyalar (CV, obyektivka, OCR, tarjima, imlo, …) uchun bir xil yo'l:
record_service_completion → record_category_use → try_increment (limitdan oshmaslik).
CV ga maxsus alohida yo'l yo'q.
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
        CAT_TRANSLATE: ("day", 5),
        CAT_OBYEKTIVKA: ("blocked", 0),
        CAT_CV: ("blocked", 0),
        CAT_OCR: ("blocked", 0),
        CAT_SPELL: ("day", 5),
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
        CAT_OBYEKTIVKA: ("subscription", 6),
        CAT_CV: ("subscription", 6),
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


def _batch_bucket_counts(user_id: int, bucket_keys: list[str]) -> dict[str, int]:
    """
    DB + mahalliy fayl: agar yozuv RLS tufayli bazaga tushmasa, lekin local ga
    yozilgan bo'lsa, faqat DB o'qilsa limit 'har doim to'liq' ko'rinardi — max() bilan birlashtiramiz.
    """
    uid = int(user_id)
    if not bucket_keys:
        return {}
    local_out = {k: _local_bucket_get(uid, k) for k in bucket_keys}
    try:
        from bot.services.supabase_db import db_service_bucket_get_many, has_db

        if has_db():
            db_out = db_service_bucket_get_many(uid, bucket_keys)
            # Supabase yoqilganda asosiy manba — DB.
            # Local qiymatni faqat explicit test fallback holatida (env) qo'shamiz.
            use_local_with_db = os.getenv("PLAN_QUOTA_LOCAL_FALLBACK_WITH_DB", "").strip().lower() in (
                "1",
                "true",
                "yes",
            )
            if use_local_with_db:
                return {
                    k: max(int(db_out.get(k, 0)), int(local_out.get(k, 0)))
                    for k in bucket_keys
                }
            return {k: int(db_out.get(k, 0)) for k in bucket_keys}
    except Exception as e:
        logger.debug("plan_limits batch get: %s", e)
    return local_out


def _get_bucket_count(user_id: int, bucket_key: str) -> int:
    return int(_batch_bucket_counts(int(user_id), [bucket_key]).get(bucket_key, 0))


def _local_bucket_get(user_id: int, bucket_key: str) -> int:
    try:
        if not os.path.exists(LOCAL_BUCKETS_FILE):
            return 0
        with open(LOCAL_BUCKETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return int(data.get(f"{user_id}|{bucket_key}", 0))
    except Exception:
        return 0


def _local_bucket_try_incr(user_id: int, bucket_key: str, cap: int) -> int:
    """Mahalliy fayl: cap dan oshmasin (bir serverda test; parallelda kichik race mumkin)."""
    uid = int(user_id)
    icap = int(cap)
    if icap < 1:
        return 0
    cur = _local_bucket_get(uid, bucket_key)
    if cur >= icap:
        return 0
    return _local_bucket_incr(uid, bucket_key)


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
    """
    Supabase yoqilgan bo'lsa — faqat DB (bot va API turli server/daemonda bo'lsa ham bir xil raqam).
    DB 0 qaytarsa mahalliy fayl yolg'on +1 beradi (faqat ixtiyoriy env bilan).
    """
    import os

    uid = int(user_id)
    try:
        from bot.services.supabase_db import has_db, db_service_bucket_increment

        if has_db():
            db_n = int(db_service_bucket_increment(uid, bucket_key))
            if db_n >= 1:
                return db_n
            logger.error(
                "plan_limits: Supabase bucket +1 ishlamadi (user=%s key=%s). "
                "Supabase SQL Editor: supabase/service_usage_buckets.sql va supabase/rpc_quota_atomic.sql",
                uid,
                bucket_key[:100],
            )
            if os.getenv("PLAN_QUOTA_LOCAL_FALLBACK_WITH_DB", "").strip().lower() in (
                "1",
                "true",
                "yes",
            ):
                logger.warning("plan_limits: PLAN_QUOTA_LOCAL_FALLBACK_WITH_DB=1 — faqat bitta serverda test uchun")
                return _local_bucket_incr(uid, bucket_key)
            return 0
    except Exception as e:
        logger.debug("plan_limits db incr: %s", e)
    return _local_bucket_incr(uid, bucket_key)


def _try_incr_bucket(user_id: int, bucket_key: str, cap: int) -> int:
    """
    Limit bilan atomik +1 (Supabase RPC). Admin emas foydalanuvchilar uchun —
    parallel so‘rovlarda ishlatilgan soni limitdan oshmaydi.
    """
    import os

    uid = int(user_id)
    icap = int(cap)
    if icap < 1:
        return 0
    try:
        from bot.services.supabase_db import db_service_bucket_try_increment, has_db

        if has_db():
            db_n = int(db_service_bucket_try_increment(uid, bucket_key, icap))
            if db_n >= 1:
                return db_n
            # 0 = limit to‘ldi yoki RPC yo‘q / xato; faqat haqiqiy nosozlikda error
            cur_after = _get_bucket_count(uid, bucket_key)
            if cur_after >= icap:
                return 0
            logger.error(
                "plan_limits: bucket +1 limit bilan ishlamadi (user=%s key=%s cap=%s). "
                "Supabase SQL: try_increment_service_bucket RPC (run_quota_setup_in_sql_editor.sql).",
                uid,
                bucket_key[:100],
                icap,
            )
            if os.getenv("PLAN_QUOTA_LOCAL_FALLBACK_WITH_DB", "").strip().lower() in (
                "1",
                "true",
                "yes",
            ):
                logger.warning(
                    "plan_limits: PLAN_QUOTA_LOCAL_FALLBACK_WITH_DB=1 — mahalliy try (test)"
                )
                return _local_bucket_try_incr(uid, bucket_key, icap)
            return 0
    except Exception as e:
        logger.debug("plan_limits db try_incr: %s", e)
    return _local_bucket_try_incr(uid, bucket_key, icap)


def _assemble_category_status(
    user_id: int,
    category: str,
    plan: str,
    mode: str,
    cap: int | None,
    label: str,
    bkey: str | None,
    counts: dict[str, int],
) -> dict[str, Any]:
    """category_status va user_limits_breakdown uchun umumiy jadval."""
    uid = int(user_id)
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

    used_raw = int(counts.get(bkey, 0))
    lim = int(cap or 0)
    rem = max(0, lim - used_raw)
    used = min(used_raw, lim)
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
        "used_raw": used_raw,
        "limit": lim,
        "remaining": rem,
        "period_note": pnote,
    }


def category_quota_for_response(user_id: int, category: str) -> dict[str, Any]:
    """API javobi: qolgan limit / ishlatilgan (web_quota_after dan keyin)."""
    st = category_status(int(user_id), category)
    return {
        "category": category,
        "unlimited": bool(st.get("unlimited")),
        "blocked": bool(st.get("blocked")),
        "used": st.get("used"),
        "limit": st.get("limit"),
        "remaining": st.get("remaining"),
        "period": st.get("period_note"),
    }


def category_status(user_id: int, category: str) -> dict[str, Any]:
    """Bitta kategoriya: used, limit, remaining, unlimited, blocked, label, period_note."""
    from bot.services.settings_service import get_active_plan_code

    uid = int(user_id)
    plan = get_active_plan_code(uid)
    mode, cap = _plan_limits(plan).get(category, ("blocked", 0))
    label = category_label_uz(category)

    # Bir martalik 5 000 so'm (admin tasdiqidan keyin) — CV / obyektivka bitta eksport.
    if plan == "free":
        try:
            from bot.services.supabase_db import has_db, db_user_has_cv_access, db_user_has_objective_access

            if has_db():
                if category == CAT_CV and db_user_has_cv_access(uid):
                    bkey_po = f"paid_once:{CAT_CV}:{uid}"
                    counts_po = _batch_bucket_counts(uid, [bkey_po])
                    return _assemble_category_status(
                        uid, category, plan, "subscription", 1, label, bkey_po, counts_po
                    )
                if category == CAT_OBYEKTIVKA and db_user_has_objective_access(uid):
                    bkey_po = f"paid_once:{CAT_OBYEKTIVKA}:{uid}"
                    counts_po = _batch_bucket_counts(uid, [bkey_po])
                    return _assemble_category_status(
                        uid, category, plan, "subscription", 1, label, bkey_po, counts_po
                    )
        except Exception as e:
            logger.debug("category_status paid_once: %s", e)

    bkey: str | None = None
    if mode not in ("unlimited", "blocked") and cap != 0:
        bkey = resolve_bucket_key(uid, category, mode)
    keys = [bkey] if bkey else []
    counts = _batch_bucket_counts(uid, keys)
    return _assemble_category_status(uid, category, plan, mode, cap, label, bkey, counts)


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
    Muvaffaqiyatli xizmatdan keyin chaqiriladi (har qanday CAT_* uchun bir xil).
    False = cheksiz/blocked yoki bucket yo'q (increment qilinmadi).

    Oddiy foydalanuvchi: limit bilan atomik +1 (_try_incr_bucket). Admin: audit uchun
    cheksiz o‘sish (_incr_bucket). Balans matnida ishlatilgan ko‘rinishi: min(raw, limit).
    """
    uid = int(user_id)
    st = category_status(uid, category)
    if st.get("unlimited"):
        return True
    if st.get("blocked"):
        return False
    from bot.services.settings_service import get_active_plan_code

    plan = get_active_plan_code(uid)
    # Free + bir martalik to'lov: bucket + flag (flag faqat muvaffaqiyatli +1 dan keyin o'chadi).
    if plan == "free" and category in (CAT_CV, CAT_OBYEKTIVKA):
        try:
            from bot.services.supabase_db import (
                has_db,
                db_grant_cv_access,
                db_grant_objective_access,
                db_user_has_cv_access,
                db_user_has_objective_access,
            )

            if has_db():
                if category == CAT_CV and db_user_has_cv_access(uid):
                    bkey_po = f"paid_once:{CAT_CV}:{uid}"
                    inc = _try_incr_bucket(uid, bkey_po, 1)
                    if inc >= 1:
                        db_grant_cv_access(uid, False)
                        return True
                    return False
                if category == CAT_OBYEKTIVKA and db_user_has_objective_access(uid):
                    bkey_po = f"paid_once:{CAT_OBYEKTIVKA}:{uid}"
                    inc = _try_incr_bucket(uid, bkey_po, 1)
                    if inc >= 1:
                        db_grant_objective_access(uid, False)
                        return True
                    return False
        except Exception as e:
            logger.debug("record_category_use paid_once: %s", e)

    mode, cap = _plan_limits(plan).get(category, ("blocked", 0))
    if mode in ("unlimited", "blocked"):
        return mode == "unlimited"
    bkey = resolve_bucket_key(uid, category, mode)
    if not bkey:
        return False
    cap_int = int(cap or 0)
    from bot.services.admin_service import is_admin

    if is_admin(uid):
        inc = _incr_bucket(uid, bkey)
    else:
        inc = _try_incr_bucket(uid, bkey, cap_int)
    if inc < 1:
        logger.error(
            "record_category_use: bucket yozilmadi (user=%s category=%s key=%s). "
            "Supabase jadval/RPC yoki PLAN_QUOTA_LOCAL_FALLBACK_WITH_DB=1 (faqat test).",
            uid,
            category,
            bkey[:100],
        )
        return False
    try:
        from bot.services.supabase_db import db_log_usage

        db_log_usage(uid, f"quota:{category}", {"bucket": bkey})
    except Exception:
        pass
    return True


def user_limits_breakdown(user_id: int, plan: str | None = None) -> list[dict[str, Any]]:
    """API / balans uchun barcha kategoriyalar ro'yxati (category_status — paid_once ham)."""
    from bot.services.settings_service import get_active_plan_code

    uid = int(user_id)
    if plan is None:
        plan = get_active_plan_code(uid)

    out: list[dict[str, Any]] = []
    for cat in _ORDER:
        st = category_status(uid, cat)
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
            line["exhausted"] = False
            line["display"] = f"{st['label']}: ♾ cheksiz"
        elif st["blocked"]:
            line["exhausted"] = False
            if cat in (CAT_CV, CAT_OBYEKTIVKA):
                try:
                    from bot.services.pricing import SINGLE_DOC_PRICE_UZS

                    p = int(SINGLE_DOC_PRICE_UZS)
                except Exception:
                    p = 5000
                line["display"] = f"{st['label']}: {p} so'm (bir martalik to'lov)"
            else:
                line["display"] = f"{st['label']}: — (tarifda yo'q)"
        else:
            u = st.get("used", 0)
            l = st.get("limit", 0)
            r = st.get("remaining", 0)
            pn = st.get("period_note", "")
            exhausted = int(r or 0) <= 0
            line["exhausted"] = exhausted
            tail = " — ⚠️ limit tugadi" if exhausted else ""
            line["display"] = (
                f"{st['label']}: ishlatilgan {u}, limit {l} ({pn}), qoldi {r}{tail}"
            )
        out.append(line)
    return out


def block_reason_for_user_uz(user_id: int, category: str) -> str:
    uid = int(user_id)
    if can_use_category(uid, category):
        return ""
    st = category_status(uid, category)
    if st.get("blocked"):
        if category in (CAT_CV, CAT_OBYEKTIVKA):
            try:
                from bot.services.pricing import SINGLE_DOC_PRICE_UZS

                p = int(SINGLE_DOC_PRICE_UZS)
            except Exception:
                p = 5000
            return (
                f"❌ «{st['label']}» bir martalik — veb-formada {p} so'm to'lov (skrinshot), "
                "admin tasdiqlagach faylni yuklab oling."
            )
        return f"❌ «{st['label']}» hozirgi tarifda yo'q. Standard yoki Premium oling."
    if st.get("unlimited"):
        return ""
    # WebApp/Bot UX requirement: consistent paywall copy for core features.
    if category in (CAT_SPELL, CAT_TRANSLATE, CAT_TRANSLIT):
        return "Limit reached. Upgrade to Premium"
    return (
        f"⛔️ «{st['label']}» limiti tugadi ({st.get('period_note', '')}). "
        f"Berilgan: {st.get('used', 0)}/{st.get('limit', 0)}. "
        "Tarifni yangilang yoki keyingi davrni kuting."
    )


def reset_plan_quotas_on_activation(user_id: int, plan: str | None = None) -> None:
    """
    Yangi tarif/obuna aktivatsiyasida joriy davr bucketlarini 0ga tushiradi.
    Asosan day/month bucketlar uchun (masalan OCR kunlik limiti).
    subscription bucketlar yangi subscription id bilan baribir yangilanadi.
    """
    from bot.services.settings_service import get_active_plan_code

    uid = int(user_id)
    p = (plan or get_active_plan_code(uid) or "free").strip().lower()
    limits = _plan_limits(p)

    keys: list[str] = []
    for cat, (mode, cap) in limits.items():
        if mode in ("day", "month") and int(cap or 0) > 0:
            bk = resolve_bucket_key(uid, cat, mode)
            if bk:
                keys.append(bk)
    if not keys:
        return

    # Local fallback bucket file reset
    try:
        if os.path.exists(LOCAL_BUCKETS_FILE):
            with open(LOCAL_BUCKETS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            changed = False
            for bk in keys:
                k = f"{uid}|{bk}"
                if k in data:
                    data.pop(k, None)
                    changed = True
            if changed:
                with open(LOCAL_BUCKETS_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=0)
    except Exception as e:
        logger.debug("reset_plan_quotas_on_activation local: %s", e)

    # Supabase bucket reset
    try:
        from bot.services.supabase_db import has_db, db_service_buckets_delete_many

        if has_db():
            db_service_buckets_delete_many(uid, keys)
    except Exception as e:
        logger.debug("reset_plan_quotas_on_activation db: %s", e)
