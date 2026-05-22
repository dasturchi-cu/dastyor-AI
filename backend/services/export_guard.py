"""Bitta foydalanuvchi uchun parallel CV/Oby eksportni oldini olish (RAM + Supabase)."""
from __future__ import annotations

import asyncio
import logging
import time

from fastapi import HTTPException

logger = logging.getLogger(__name__)

_LOCKS: dict[str, asyncio.Lock] = {}
_LAST_SEND_TS: dict[str, float] = {}
_COOLDOWN_SEC = float(__import__("os").getenv("DOC_EXPORT_COOLDOWN_SEC", "50"))
_STALE_PENDING_SEC = float(__import__("os").getenv("DOC_EXPORT_PENDING_STALE_SEC", "90"))


def _key(uid: int, category: str) -> str:
    return f"{int(uid)}:{(category or '').strip().lower()}"


def _pending_bucket(uid: int, category: str) -> str:
    cat = (category or "").strip().lower()
    return f"doc_send_pending:{cat}:{int(uid)}"


def _done_bucket(uid: int, category: str) -> str:
    cat = (category or "").strip().lower()
    return f"doc_send_done:{cat}:{int(uid)}"


def delivery_bucket_keys(uid: int, category: str) -> list[str]:
    return [_pending_bucket(uid, category), _done_bucket(uid, category)]


def clear_document_delivery_buckets(uid: int, category: str) -> None:
    """Yangi to'lov tasdiqlanganda — qayta 1 marta yuborishga ruxsat."""
    try:
        from bot.services.supabase_db import db_service_buckets_delete_many, has_db

        if has_db():
            db_service_buckets_delete_many(int(uid), delivery_bucket_keys(uid, category))
    except Exception as e:
        logger.debug("clear_document_delivery_buckets uid=%s: %s", uid, e)


def _pending_is_stale(uid: int, category: str) -> bool:
    """Qotgan doc_send_pending — yangi to‘lov / qayta urinish uchun."""
    try:
        from datetime import datetime, timezone

        from bot.services.supabase_db import db_service_bucket_row, has_db

        if not has_db():
            return True
        row = db_service_bucket_row(int(uid), _pending_bucket(int(uid), category))
        if not row or int(row.get("count") or 0) < 1:
            return False
        raw = row.get("updated_at")
        if not raw:
            return True
        if isinstance(raw, str):
            ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        elif isinstance(raw, datetime):
            ts = raw
        else:
            return True
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        return age >= _STALE_PENDING_SEC
    except Exception:
        return True


def _db_claim_export_slot(uid: int, category: str) -> None:
    """Bir nechta Railway workerda ham bitta yuborish (Supabase bucket)."""
    try:
        from bot.services.supabase_db import (
            db_service_bucket_get,
            db_service_bucket_try_increment,
            db_service_buckets_delete_many,
            has_db,
        )

        if not has_db():
            return
        u = int(uid)
        done_key = _done_bucket(u, category)
        pending_key = _pending_bucket(u, category)
        if int(db_service_bucket_get(u, done_key) or 0) >= 1:
            raise HTTPException(
                status_code=409,
                detail="✅ Allaqachon yuborilgan. Yangi to‘lov kerak.",
            )
        if int(db_service_bucket_get(u, pending_key) or 0) >= 1:
            if _pending_is_stale(u, category):
                db_service_buckets_delete_many(u, [pending_key])
            else:
                raise HTTPException(
                    status_code=409,
                    detail="⏳ Tayyorlanmoqda. 1 daqiqa kuting.",
                )
        inc = int(db_service_bucket_try_increment(u, pending_key, 1) or 0)
        if inc < 1:
            db_service_buckets_delete_many(u, [pending_key])
            inc = int(db_service_bucket_try_increment(u, pending_key, 1) or 0)
        if inc < 1:
            logger.warning("export pending claim failed uid=%s cat=%s — clear", u, category)
            db_service_buckets_delete_many(u, [pending_key])
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("export_guard db claim failed uid=%s: %s", uid, e)


def _db_release_pending(uid: int, category: str) -> None:
    try:
        from bot.services.supabase_db import db_service_buckets_delete_many, has_db

        if has_db():
            db_service_buckets_delete_many(int(uid), [_pending_bucket(int(uid), category)])
    except Exception:
        pass


def _db_mark_delivered(uid: int, category: str) -> None:
    try:
        from bot.services.supabase_db import (
            db_service_bucket_try_increment,
            db_service_buckets_delete_many,
            has_db,
        )

        if has_db():
            u = int(uid)
            db_service_bucket_try_increment(u, _done_bucket(u, category), 1)
            db_service_buckets_delete_many(u, [_pending_bucket(u, category)])
    except Exception as e:
        logger.warning("export_guard db mark delivered uid=%s: %s", uid, e)


async def begin_document_export(
    uid: int,
    category: str,
    *,
    hold_process_lock: bool = True,
) -> None:
    """Eksport boshlanishi. Fon yuborishda hold_process_lock=False (qulflanib qolmasin)."""
    _db_claim_export_slot(uid, category)

    if not hold_process_lock:
        return

    k = _key(uid, category)
    if k not in _LOCKS:
        _LOCKS[k] = asyncio.Lock()
    lock = _LOCKS[k]
    if lock.locked():
        _db_release_pending(uid, category)
        raise HTTPException(
            status_code=409,
            detail="⏳ Tayyorlanmoqda. Kuting.",
        )
    now = time.monotonic()
    last = _LAST_SEND_TS.get(k, 0.0)
    if last and (now - last) < _COOLDOWN_SEC:
        _db_release_pending(uid, category)
        raise HTTPException(
            status_code=409,
            detail="✅ Yaqinda yuborilgan. Yangi to‘lov kerak.",
        )
    await lock.acquire()


def mark_document_export_sent(uid: int, category: str) -> None:
    _LAST_SEND_TS[_key(uid, category)] = time.monotonic()
    _db_mark_delivered(uid, category)
    release_document_export(uid, category)


def release_document_export(uid: int, category: str) -> None:
    _db_release_pending(uid, category)
    k = _key(uid, category)
    lock = _LOCKS.get(k)
    if lock and lock.locked():
        try:
            lock.release()
        except RuntimeError:
            pass
