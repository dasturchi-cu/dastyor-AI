from __future__ import annotations

from typing import Any

from backend.celery_app import celery_app
from backend.services.paddle_ocr_runtime import (
    ocr_extract_text_from_bytes,
    ocr_image_to_docx_from_bytes,
)
from backend.services.supabase_storage import create_signed_url, download_bytes, upload_bytes_for_user


@celery_app.task(name="ocr.extract_text")
def ocr_extract_text(image_bytes: bytes) -> dict[str, Any]:
    return ocr_extract_text_from_bytes(image_bytes)


@celery_app.task(name="ocr.image_to_docx")
def ocr_image_to_docx(image_bytes: bytes) -> dict[str, Any]:
    return ocr_image_to_docx_from_bytes(image_bytes)


@celery_app.task(name="files.process_v1")
def process_file_v1(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Async file processing worker:
      - download bytes from storage
      - extract text
      - process (spellcheck|translit_auto|translate_auto)
      - upload output as txt
    """
    import os
    from datetime import datetime

    from backend.services.auto_script import auto_cyrillic_latin

    user_id = int(payload.get("user_id") or 0)
    action = str(payload.get("action") or "").strip().lower()
    target_lang = str(payload.get("target_lang") or "").strip().lower()
    filename = str(payload.get("filename") or "upload.txt")
    storage = payload.get("storage") or {}
    bucket = str(storage.get("bucket") or "")
    path = str(storage.get("path") or "")

    if not user_id or not bucket or not path:
        return {"ok": False, "error": "storage_missing"}

    raw = download_bytes(bucket=bucket, path=path)
    if not raw:
        return {"ok": False, "error": "storage_download_failed"}

    from bot.services.document_text_extract import extract_plain_text_from_bytes

    try:
        text = extract_plain_text_from_bytes(filename, raw)
    except Exception as e:
        return {"ok": False, "error": "extract_failed", "detail": str(e)[:200]}

    if not (text or "").strip():
        return {"ok": False, "error": "no_text_extracted"}

    meta: dict[str, Any] = {"filename": filename, "chars": len(text or "")}
    out_text = ""

    if action == "spellcheck":
        from bot.services.ai_service import check_spelling_text

        corrected, fixes = _run_async(check_spelling_text(text))
        out_text = corrected or ""
        meta["fixed"] = int(fixes or 0)
    elif action == "translit_auto":
        res = auto_cyrillic_latin(text)
        out_text = res.result or ""
        meta["detected"] = res.detected
        meta["direction"] = res.direction
        meta["stats"] = res.stats
    elif action == "translate_auto":
        if target_lang not in ("uz", "ru", "en"):
            return {"ok": False, "error": "target_lang_invalid"}
        # naive direction selection (match web logic)
        src = "uz"
        try:
            from langdetect import detect  # type: ignore

            sample = (text or "").strip().replace("\u0000", "")[:2500]
            d = (detect(sample) or "").lower()
            if d.startswith("ru"):
                src = "ru"
            elif d.startswith("en"):
                src = "en"
            else:
                src = "uz"
        except Exception:
            src = "uz"
        if src == target_lang:
            out_text = (text or "").strip()
            meta["source_lang"] = src
            meta["target_lang"] = target_lang
            meta["direction"] = "none"
        else:
            direction_map = {
                ("uz", "en"): "uz_en",
                ("en", "uz"): "en_uz",
                ("ru", "uz"): "ru_uz",
                ("uz", "ru"): "uz_ru",
                ("ru", "en"): "ru_en",
                ("en", "ru"): "en_ru",
            }
            direction = direction_map.get((src, target_lang))
            if not direction:
                return {"ok": False, "error": "direction_missing"}
            from bot.services.ai_service import translate_text

            out = _run_async(translate_text(text, direction))
            out_text = out or ""
            meta["source_lang"] = src
            meta["target_lang"] = target_lang
            meta["direction"] = direction
    else:
        return {"ok": False, "error": "action_invalid"}

    base = os.path.splitext(os.path.basename(filename))[0] or "document"
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_name = f"{base}_{action}_{ts}.txt"
    up = upload_bytes_for_user(telegram_id=user_id, filename=out_name, raw=(out_text or "").encode("utf-8"))
    if not up:
        return {"ok": True, "text": out_text, "meta": meta, "storage_out": None}
    signed = create_signed_url(bucket=up.bucket, path=up.path, expires_in=3600)
    return {
        "ok": True,
        "action": action,
        "text": out_text,
        "meta": meta,
        "storage_out": {"bucket": up.bucket, "path": up.path, "public_url": up.public_url, "signed_url": signed},
    }


def _run_async(awaitable):
    """Run an async function inside a Celery sync task."""
    import asyncio

    return asyncio.run(awaitable)
