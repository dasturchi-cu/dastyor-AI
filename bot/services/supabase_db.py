"""
Supabase DB — Ma'lumotlar bazasi bilan ishlash
Serverda SUPABASE_SERVICE_ROLE_KEY tavsiya (RLS ostida yozish uchun).
"""
import os
import logging
import time
from datetime import datetime, date
from typing import Optional

logger = logging.getLogger(__name__)

_client = None
_service_role_warned = False
_disabled_until_ts = 0.0
_last_disable_reason = ""
_DB_DISABLE_SECONDS = int(os.getenv("SUPABASE_DISABLE_SECONDS", "300"))


def _maybe_warn_service_role():
    """Anon kalit bilan RLS yozuvlarni bloklaydi — bir marta ogohlantiramiz."""
    global _service_role_warned
    if _service_role_warned:
        return
    if os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        return
    if not os.getenv("SUPABASE_URL"):
        return
    _service_role_warned = True
    logger.warning(
        "SUPABASE_SERVICE_ROLE_KEY sozlanmagan. Agar jadvallarda RLS yoqilgan bo'lsa, "
        "bot/Web API yozuvlari bazaga TUSHMAYDI. "
        "Supabase → Settings → API → service_role kalitini server env ga qo'shing. "
        "Yoki supabase/rls_fix_backend_writes.sql ni SQL Editor da ishga tushiring."
    )


def _log_write_error(context: str, exc: Exception) -> None:
    msg = str(exc).lower()
    if "row-level security" in msg or "42501" in msg or "permission denied" in msg or "pgrst" in msg:
        logger.error(
            "%s: %s — ehtimol RLS yoki noto'g'ri kalit. "
            "Serverda SUPABASE_SERVICE_ROLE_KEY qo'ying yoki rls_fix_backend_writes.sql.",
            context,
            exc,
        )
    else:
        logger.error("%s: %s", context, exc)


def _get_client():
    global _client
    now = time.time()
    if _disabled_until_ts > now:
        return None
    if _client is not None:
        return _client
    url = (os.getenv("SUPABASE_URL") or "").strip().strip('"').strip("'")
    # Prefer service role for server-side writes (RLS policies).
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY") or "").strip().strip('"').strip("'")
    if not url or not key:
        return None
    try:
        from supabase import create_client
        _client = create_client(url, key)
        logger.info("Supabase client initialized")
        _maybe_warn_service_role()
        return _client
    except Exception as e:
        logger.warning(f"Supabase init failed: {e}")
        return None


def _mark_temporarily_unavailable(exc: Exception):
    """
    Disable Supabase calls for a cooldown window on network-level failures.
    This prevents repeated noisy errors and allows local JSON fallback.
    """
    global _client, _disabled_until_ts, _last_disable_reason
    msg = str(exc or "").lower()
    # Faqat vaqtincha tarmoq uzilishlari — DNS (Name or service not known) ko'pincha
    # noto'g'ri SUPABASE_URL / hostname bo'ladi; 300s o'chirish foydasiz va zararli.
    transient_markers = (
        "connection refused",
        "connect timeout",
        "network is unreachable",
        "timed out",
        "connection reset",
        "broken pipe",
    )
    dns_markers = (
        "name or service not known",
        "temporary failure in name resolution",
        "nodename nor servname provided",
        "failed to resolve",
    )
    if any(m in msg for m in dns_markers):
        logger.error(
            "Supabase DNS/host xato — Railway .env da SUPABASE_URL to'g'rimi? (https://xxxx.supabase.co): %s",
            exc,
        )
        return

    if any(marker in msg for marker in transient_markers):
        _client = None
        _disabled_until_ts = time.time() + _DB_DISABLE_SECONDS
        reason = str(exc)[:200]
        if reason != _last_disable_reason:
            _last_disable_reason = reason
            logger.warning(
                "Supabase temporarily disabled for %ss due to connectivity issue: %s",
                _DB_DISABLE_SECONDS,
                reason,
            )


def has_db() -> bool:
    return _get_client() is not None


# ── pending obyektivka (voice → /api/get_oby_data) ───────────────────────────
def db_save_pending_oby(user_id: int, data: dict) -> bool:
    """Saqlangan JSON Web App forma avto-to'ldirish uchun (Supabase bo'lsa)."""
    c = _get_client()
    if not c or not isinstance(data, dict):
        return False
    uid = int(user_id)
    now = datetime.utcnow().isoformat()
    payload = {"pending_oby_json": data, "pending_oby_updated_at": now}
    try:
        chk = c.table("users").select("id").eq("id", uid).limit(1).execute()
        if chk.data:
            c.table("users").update(payload).eq("id", uid).execute()
        else:
            c.table("users").insert(
                {
                    "id": uid,
                    "telegram_id": uid,
                    "first_name": "",
                    "username": "",
                    "chat_id": uid,
                    **payload,
                }
            ).execute()
        return True
    except Exception as e:
        _log_write_error("db_save_pending_oby", e)
        return False


def db_get_pending_oby(user_id: int) -> Optional[dict]:
    c = _get_client()
    if not c:
        return None
    try:
        r = c.table("users").select("pending_oby_json").eq("id", int(user_id)).limit(1).execute()
        if not r.data:
            return None
        raw = r.data[0].get("pending_oby_json")
        if isinstance(raw, dict) and raw:
            return raw
        return None
    except Exception as e:
        _log_write_error("db_get_pending_oby", e)
        return None


def db_clear_pending_oby(user_id: int) -> bool:
    c = _get_client()
    if not c:
        return False
    try:
        c.table("users").update(
            {"pending_oby_json": None, "pending_oby_updated_at": None}
        ).eq("id", int(user_id)).execute()
        return True
    except Exception as e:
        _log_write_error("db_clear_pending_oby", e)
        return False


# ── users ────────────────────────────────────────────────────────────────────
def db_get_user(user_id: int | str) -> Optional[dict]:
    c = _get_client()
    if not c:
        return None
    try:
        r = c.table("users").select("*").eq("id", int(user_id)).execute()
        rows = r.data
        if not rows:
            return None
        row = rows[0]
        return {
            "id": row["id"],
            "first_name": row.get("first_name", ""),
            "username": row.get("username"),
            "chat_id": row.get("chat_id"),
            "joined_at": row.get("joined_at"),
            "last_active": row.get("last_active"),
            "activity_count": row.get("activity_count", 0),
            "files_processed": row.get("files_processed", 0),
            "sessions": row.get("sessions", 0),
            "lang": row.get("lang", "uz_lat"),
            "is_banned": row.get("is_banned", False),
            "ban_reason": row.get("ban_reason"),
            "ban_date": row.get("ban_date"),
            "blocked_bot": row.get("blocked_bot", False),
            "last_service": row.get("last_service"),
            "user_plan": row.get("user_plan", "standard"),
            "usage_count": row.get("usage_count", 0),
            "limit_count": row.get("limit_count"),
        }
    except Exception as e:
        _mark_temporarily_unavailable(e)
        _log_write_error("db_get_user", e)
        return None


def db_upsert_user(user_id: int, first_name: str = "", username: str = None,
                   chat_id: int = None, command: str = None) -> bool:
    c = _get_client()
    if not c:
        return False
    now = datetime.utcnow().isoformat()
    # Supabase users.first_name ko'pincha NOT NULL — hech qachon null yubormaymiz
    fn = ((first_name or "").strip() or "User")[:200]
    un = ("" if username is None else str(username))[:200]
    cid = int(chat_id if chat_id is not None else user_id)
    tid = int(user_id)

    # 1) qator bormi? (faqat id — sessions ustuni bo'lmasa ham ishlaydi)
    r = None
    try:
        r = c.table("users").select("id,sessions").eq("id", tid).limit(1).execute()
    except Exception:
        try:
            r = c.table("users").select("id").eq("id", tid).limit(1).execute()
        except Exception:
            r = None
    exists = bool(r and r.data)

    # 2) update path
    if exists:
        try:
            upd = {
                "first_name": fn,
                "last_active": now,
                "telegram_id": tid,
            }
            if username is not None:
                upd["username"] = un
            if chat_id is not None:
                upd["chat_id"] = cid
            c.table("users").update(upd).eq("id", tid).execute()
        except Exception:
            # If some columns like chat_id/sessions don't exist, still keep row alive.
            try:
                c.table("users").update({"last_active": now, "telegram_id": tid}).eq("id", tid).execute()
            except Exception as e:
                _mark_temporarily_unavailable(e)
                _log_write_error("db_upsert_user update", e)
                return False

        # optional sessions increment
        if command == "start":
            try:
                sess = 0
                if r and r.data and isinstance(r.data, list) and len(r.data) > 0:
                    sess = r.data[0].get("sessions", 0) or 0
                c.table("users").update({"sessions": int(sess) + 1}).eq("id", tid).execute()
            except Exception:
                # ignore sessions column drift
                pass
        return True

    # 3) yangi foydalanuvchi: har bir urinishda first_name/username/chat_id bo'lishi SHART
    # (oldingi {"id", "last_active"} fallback NOT NULL first_name ni buzgan)
    # Kam urinish — har biri 2 ta HTTP (upsert+insert) bo'lmasligi uchun avvalo eng to'liq, keyin minimal
    base = {
        "id": tid,
        "telegram_id": tid,
        "first_name": fn,
        "username": un,
        "chat_id": cid,
        "last_active": now,
    }
    payload_candidates = [
        {
            **base,
            "activity_count": 1,
            "sessions": 1 if command == "start" else 0,
        },
        dict(base),
    ]

    last_e: Exception | None = None
    for payload in payload_candidates:
        try:
            c.table("users").upsert(payload).execute()
            return True
        except Exception as e:
            last_e = e
            try:
                c.table("users").insert(payload).execute()
                return True
            except Exception as e2:
                last_e = e2
                continue

    if last_e:
        _mark_temporarily_unavailable(last_e)
        _log_write_error("db_upsert_user insert/upsert", last_e)
    return False


def db_update_user_field(user_id: int, **kwargs) -> bool:
    c = _get_client()
    if not c:
        return False
    try:
        c.table("users").update(kwargs).eq("id", user_id).execute()
        return True
    except Exception as e:
        _mark_temporarily_unavailable(e)
        logger.error(f"db_update_user_field: {e}")
        return False


def db_increment_files(user_id: int, service_name: str = None) -> bool:
    c = _get_client()
    if not c:
        return False
    try:
        r = c.table("users").select("files_processed").eq("id", user_id).execute()
        if not r.data:
            db_upsert_user(int(user_id), "", None, int(user_id), command=None)
            r = c.table("users").select("files_processed").eq("id", user_id).execute()
        if r.data:
            count = r.data[0].get("files_processed", 0) + 1
            upd = {"files_processed": count}
            if service_name:
                upd["last_service"] = service_name
            c.table("users").update(upd).eq("id", user_id).execute()
            return True
        _log_write_error("db_increment_files", RuntimeError("users qatori topilmadi / yozilmadi"))
        return False
    except Exception as e:
        _mark_temporarily_unavailable(e)
        _log_write_error("db_increment_files", e)
        return False


# ── daily_usage ──────────────────────────────────────────────────────────────
def db_get_usage(user_id: int) -> int:
    c = _get_client()
    if not c:
        return 0
    try:
        today = date.today().isoformat()
        r = c.table("daily_usage").select("count").eq("user_id", user_id).eq("usage_date", today).execute()
        if r.data:
            return r.data[0].get("count", 0)
        return 0
    except Exception as e:
        _mark_temporarily_unavailable(e)
        logger.error(f"db_get_usage: {e}")
        return 0


def db_increment_usage(user_id: int) -> int:
    c = _get_client()
    if not c:
        return 0
    try:
        today = date.today().isoformat()
        r = c.table("daily_usage").select("id,count").eq("user_id", user_id).eq("usage_date", today).execute()
        if r.data:
            new_count = r.data[0].get("count", 0) + 1
            c.table("daily_usage").update({"count": new_count}).eq("id", r.data[0]["id"]).execute()
            return new_count
        try:
            c.table("daily_usage").insert({"user_id": user_id, "usage_date": today, "count": 1}).execute()
            return 1
        except Exception:
            db_upsert_user(int(user_id), "", None, int(user_id), command=None)
            c.table("daily_usage").insert({"user_id": user_id, "usage_date": today, "count": 1}).execute()
            return 1
    except Exception as e:
        _mark_temporarily_unavailable(e)
        _log_write_error("db_increment_usage", e)
        return 0


def db_reset_daily_usage(user_id: int) -> bool:
    """Premium tasdiqdan keyin kunlik bepul limit hisobini 0 ga (daily_usage)."""
    c = _get_client()
    if not c:
        return False
    try:
        today = date.today().isoformat()
        r = c.table("daily_usage").select("id").eq("user_id", user_id).eq("usage_date", today).execute()
        if r.data:
            c.table("daily_usage").update({"count": 0}).eq("id", r.data[0]["id"]).execute()
        return True
    except Exception as e:
        _mark_temporarily_unavailable(e)
        logger.error(f"db_reset_daily_usage: {e}")
        return False


def db_log_usage(user_id: int, action: str, metadata: dict | None = None) -> bool:
    """usage_logs jadvaliga audit (ustunlar bo'lmasa — sessiz o'tkaziladi)."""
    c = _get_client()
    if not c:
        return False
    try:
        payload = {
            "user_id": int(user_id),
            "action": (action or "unknown")[:120],
            "created_at": datetime.utcnow().isoformat(),
        }
        if metadata:
            payload["metadata"] = metadata
        c.table("usage_logs").insert(payload).execute()
        return True
    except Exception as e:
        logger.debug("db_log_usage skip or schema drift: %s", e)
        return False


# ── bot_settings ─────────────────────────────────────────────────────────────
def db_get_daily_limit() -> Optional[int]:
    c = _get_client()
    if not c:
        return None
    try:
        r = c.table("bot_settings").select("daily_limit").eq("id", 1).execute()
        if r.data:
            return r.data[0].get("daily_limit", 10)
        return 10
    except Exception as e:
        _mark_temporarily_unavailable(e)
        logger.error(f"db_get_daily_limit: {e}")
        return None


def db_get_maintenance_mode() -> Optional[bool]:
    c = _get_client()
    if not c:
        return None
    try:
        r = c.table("bot_settings").select("maintenance_mode").eq("id", 1).execute()
        if r.data:
            return bool(r.data[0].get("maintenance_mode", False))
        return False
    except Exception as e:
        _mark_temporarily_unavailable(e)
        logger.error(f"db_get_maintenance_mode: {e}")
        return None


def db_set_maintenance_mode(enabled: bool) -> bool:
    c = _get_client()
    if not c:
        return False
    try:
        existing = c.table("bot_settings").select("id").eq("id", 1).execute()
        if existing.data:
            c.table("bot_settings").update({"maintenance_mode": bool(enabled)}).eq("id", 1).execute()
        else:
            c.table("bot_settings").insert({
                "id": 1,
                "daily_limit": 10,
                "maintenance_mode": bool(enabled),
            }).execute()
        return True
    except Exception as e:
        _mark_temporarily_unavailable(e)
        logger.error(f"db_set_maintenance_mode: {e}")
        return False


# ── premium (premium_subscriptions) ──────────────────────────────────────────
def _parse_ts(val) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=None) if val.tzinfo else val
    s = str(val).strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def db_is_premium(user_id: int) -> bool:
    """
    True faqat faol to'lovli obuna bo'lsa (premium yoki standard tarif).
    Muddati tugagach avtomatik False — limitlar qaytadi (/start maxsus emas).
    """
    c = _get_client()
    if not c:
        return False
    try:
        uid = int(user_id)
        now = datetime.utcnow()
        try:
            r = (
                c.table("premium_subscriptions")
                .select("id,plan_type,status,expire_date,end_date")
                .eq("user_id", uid)
                .limit(40)
                .execute()
            )
        except Exception:
            r = c.table("premium_subscriptions").select("*").eq("user_id", uid).limit(40).execute()

        rows = sorted(
            r.data or [],
            key=lambda x: int(x.get("id") or 0),
            reverse=True,
        )
        for row in rows:
            st = (row.get("status") or "active").strip().lower()
            if st in ("cancelled", "rejected", "expired"):
                continue
            exp = _parse_ts(row.get("expire_date")) or _parse_ts(row.get("end_date"))
            if exp and exp >= now:
                return True
        return False
    except Exception as e:
        _mark_temporarily_unavailable(e)
        logger.error(f"db_is_premium: {e}")
        return False


def db_insert_action_log(
    user_id: int,
    action_type: str,
    file_name: str | None = None,
    metadata: dict | None = None,
) -> bool:
    """
    Append one row to `logs` (preferred) or `usage_logs` if schema differs.
    action_type: ocr, cv, pdf, word, translate, translit, imlo, obyektivka_voice, ...
    """
    c = _get_client()
    if not c:
        return False
    uid = int(user_id)
    at = (action_type or "unknown")[:120]
    fn = (file_name or "")[:500] if file_name else None
    ts = datetime.utcnow().isoformat()
    base = {"user_id": uid, "action_type": at}
    if fn:
        base["file_name"] = fn
    attempts: list[dict] = [
        {**base, "created_at": ts},
        dict(base),
    ]
    if metadata:
        attempts.insert(0, {**base, "created_at": ts, "metadata": metadata})
        attempts.insert(1, {**base, "metadata": metadata})
    last_err: Exception | None = None
    for payload in attempts:
        try:
            c.table("logs").insert(payload).execute()
            return True
        except Exception as e:
            last_err = e
            continue
    # Ba'zi eski sxemalarda `action` ustuni bo'ladi, `action_type` emas
    for base in (
        {"user_id": uid, "action": at, "created_at": ts},
        {"user_id": uid, "action": at},
    ):
        alt_log = dict(base)
        if fn:
            alt_log["file_name"] = fn
        if metadata:
            alt_log["metadata"] = metadata
        try:
            c.table("logs").insert(alt_log).execute()
            return True
        except Exception as e:
            last_err = e
            continue
    try:
        alt = {"user_id": uid, "action": at, "created_at": ts}
        if metadata:
            alt["metadata"] = metadata
        c.table("usage_logs").insert(alt).execute()
        return True
    except Exception as e:
        last_err = e
    if last_err:
        _log_write_error("db_insert_action_log", last_err)
    return False


# ── premium payments flow (webapp) ─────────────────────────────────────────────
def db_create_payment(
    user_id: int,
    plan_type: str,
    amount: float,
    screenshot_url: str | None = None,
    metadata: dict | None = None,
) -> Optional[int]:
    """
    Create a pending payment row in Supabase.
    Returns payment id or None if Supabase unavailable / schema drift.
    """
    c = _get_client()
    if not c:
        return None
    try:
        plan = (plan_type or "premium").strip().lower()
        if plan not in ("standard", "premium"):
            plan = "premium"
        meta = metadata or {}
        payload = {
            "user_id": int(user_id),
            "plan_type": plan,
            "amount": float(amount),
            "currency": "UZS",
            "screenshot_url": screenshot_url,
            "status": "pending",
        }
        # Some schemas may or may not have `metadata` jsonb column.
        try:
            if meta:
                payload_with_meta = {**payload, "metadata": meta}
                res = c.table("payments").insert(payload_with_meta).execute()
            else:
                res = c.table("payments").insert(payload).execute()
        except Exception:
            res = c.table("payments").insert(payload).execute()
        if res.data and len(res.data) > 0:
            return int(res.data[0]["id"])
        return None
    except Exception as e:
        _mark_temporarily_unavailable(e)
        logger.error(f"db_create_payment error: {e}", exc_info=True)
        return None


def db_get_payment(payment_id: int) -> Optional[dict]:
    c = _get_client()
    if not c:
        return None
    try:
        r = c.table("payments").select("*").eq("id", int(payment_id)).execute()
        if r.data:
            row = r.data[0]
            return dict(row)
        return None
    except Exception as e:
        _mark_temporarily_unavailable(e)
        logger.error(f"db_get_payment error: {e}", exc_info=True)
        return None


def db_set_payment_status(
    payment_id: int,
    status: str,
    reviewed_by: int | None = None,
    admin_note: str | None = None,
) -> bool:
    c = _get_client()
    if not c:
        return False
    try:
        st = (status or "").strip().lower()
        if st not in ("approved", "rejected", "pending", "failed"):
            return False
        payload = {"status": st}
        if reviewed_by is not None:
            payload["reviewed_by"] = int(reviewed_by)
        if admin_note is not None:
            payload["admin_note"] = admin_note
        c.table("payments").update(payload).eq("id", int(payment_id)).execute()
        return True
    except Exception as e:
        _mark_temporarily_unavailable(e)
        logger.error(f"db_set_payment_status error: {e}", exc_info=True)
        return False


def db_activate_subscription(
    user_id: int,
    plan_type: str,
    start_date,
    expire_date,
    status: str = "active",
) -> bool:
    c = _get_client()
    if not c:
        return False
    try:
        plan = (plan_type or "premium").strip().lower()
        if plan not in ("standard", "premium"):
            plan = "premium"
        st = (status or "active").strip().lower()
        if st not in ("active", "expired", "pending", "cancelled"):
            st = "active"
        payload = {
            "user_id": int(user_id),
            "plan_type": plan,
            "start_date": start_date,
            "expire_date": expire_date,
            "status": st,
        }
        try:
            c.table("premium_subscriptions").insert(payload).execute()
        except Exception:
            # Ba'zi sxemalarda faqat end_date bor (expire_date emas)
            alt = {**payload, "end_date": expire_date}
            alt.pop("expire_date", None)
            c.table("premium_subscriptions").insert(alt).execute()
        # users.user_plan — ustun bo'lsa yangilaymiz
        try:
            c.table("users").update({"user_plan": "premium" if plan == "premium" else "standard"}).eq(
                "id", int(user_id)
            ).execute()
        except Exception:
            pass
        return True
    except Exception as e:
        _mark_temporarily_unavailable(e)
        logger.error(f"db_activate_subscription error: {e}", exc_info=True)
        return False


# ── get_all_users (for CRM / stats) ──────────────────────────────────────────
def db_get_all_users() -> dict:
    c = _get_client()
    if not c:
        return {}
    try:
        r = c.table("users").select("*").execute()
        out = {}
        for row in r.data or []:
            uid = str(row["id"])
            out[uid] = {
                "id": row["id"],
                "first_name": row.get("first_name", ""),
                "username": row.get("username"),
                "chat_id": row.get("chat_id"),
                "joined_at": row.get("joined_at"),
                "last_active": row.get("last_active"),
                "activity_count": row.get("activity_count", 0),
                "files_processed": row.get("files_processed", 0),
                "sessions": row.get("sessions", 0),
                "lang": row.get("lang", "uz_lat"),
                "is_banned": row.get("is_banned", False),
                "ban_reason": row.get("ban_reason"),
                "ban_date": row.get("ban_date"),
                "blocked_bot": row.get("blocked_bot", False),
                "last_service": row.get("last_service"),
            }
        return out
    except Exception as e:
        _mark_temporarily_unavailable(e)
        logger.error(f"db_get_all_users: {e}")
        return {}
