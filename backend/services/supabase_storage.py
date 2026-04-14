from __future__ import annotations

import io
import logging
import mimetypes
import os
import time
from dataclasses import dataclass

from backend.services.user_resolve import safe_filename_part

logger = logging.getLogger("dastyor.storage")


@dataclass(frozen=True)
class StorageUploadResult:
    bucket: str
    path: str
    public_url: str | None


def _get_client():
    # Reuse existing supabase client init (service role preferred)
    from bot.services.supabase_db import _get_client  # type: ignore

    return _get_client()


def storage_bucket_name() -> str:
    return (os.getenv("SUPABASE_FILES_BUCKET") or "files").strip() or "files"


def _guess_content_type(filename: str) -> str:
    ct, _ = mimetypes.guess_type(filename or "")
    return ct or "application/octet-stream"


def upload_bytes_for_user(*, telegram_id: int, filename: str, raw: bytes) -> StorageUploadResult | None:
    """
    Upload file bytes to Supabase Storage.
    Returns {bucket, path, public_url?} or None if storage/client is unavailable.
    """
    c = _get_client()
    if not c:
        # Most common production misconfig: SUPABASE_URL / keys missing in runtime env.
        logger.error(
            "Supabase storage client unavailable (SUPABASE_URL/key missing or Supabase disabled). "
            "env_has_url=%s env_has_service_role=%s env_has_anon=%s",
            bool((os.getenv("SUPABASE_URL") or "").strip()),
            bool((os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()),
            bool((os.getenv("SUPABASE_ANON_KEY") or "").strip()),
        )
        return None
    bucket = storage_bucket_name()
    safe = safe_filename_part(filename or "upload.bin", "upload.bin")
    ts = int(time.time())
    path = f"{int(telegram_id)}/{ts}_{safe}"
    content_type = _guess_content_type(safe)

    # supabase-py Storage API differs across versions. Try a few compatible call shapes.
    upload_err: Exception | None = None
    for attempt in range(1, 5):
        try:
            if attempt == 1:
                # v2 style: keyword args, bytes
                c.storage.from_(bucket).upload(
                    path=path,
                    file=raw,
                    file_options={"content-type": content_type, "upsert": True},
                )
            elif attempt == 2:
                # v2 style: file-like (most compatible)
                c.storage.from_(bucket).upload(
                    path=path,
                    file=io.BytesIO(raw),
                    file_options={"content-type": content_type, "upsert": True},
                )
            elif attempt == 3:
                # positional style (some builds accept upload(path, file, options))
                c.storage.from_(bucket).upload(
                    path,
                    io.BytesIO(raw),
                    {"content-type": content_type, "upsert": True},
                )
            else:
                # alternate option keys used in some wrappers
                c.storage.from_(bucket).upload(
                    path=path,
                    file=io.BytesIO(raw),
                    file_options={"contentType": content_type, "upsert": True},
                )
            upload_err = None
            break
        except Exception as e:
            upload_err = e
            continue

    if upload_err is not None:
        # If bucket doesn't exist / policy blocks / API differs, fail softly but log root cause.
        msg = str(upload_err)
        hint = ""
        if "not found" in msg.lower() and "bucket" in msg.lower():
            hint = "Create bucket 'files' in Supabase Storage (or set SUPABASE_FILES_BUCKET)."
        elif "row-level security" in msg.lower() or "permission" in msg.lower() or "403" in msg.lower():
            hint = "Likely Storage policy/RLS or wrong key. Ensure SUPABASE_SERVICE_ROLE_KEY is set on server."
        logger.error(
            "Supabase storage upload failed bucket=%s path=%s bytes=%s ct=%s err=%s hint=%s",
            bucket,
            path,
            len(raw) if raw is not None else 0,
            content_type,
            msg[:300],
            hint,
            exc_info=True,
        )
        return None

    public_url = None
    try:
        public_url = c.storage.from_(bucket).get_public_url(path)
        if public_url and isinstance(public_url, dict):
            public_url = public_url.get("publicUrl") or public_url.get("public_url")
        if public_url and not isinstance(public_url, str):
            public_url = None
    except Exception:
        public_url = None

    return StorageUploadResult(bucket=bucket, path=path, public_url=public_url)


def create_signed_url(*, bucket: str, path: str, expires_in: int = 3600) -> str | None:
    c = _get_client()
    if not c:
        return None
    try:
        res = c.storage.from_(bucket).create_signed_url(path, int(expires_in))
        if isinstance(res, dict):
            return res.get("signedURL") or res.get("signedUrl") or res.get("signed_url")
        return None
    except Exception:
        return None


def download_bytes(*, bucket: str, path: str) -> bytes | None:
    """
    Download object bytes from Supabase Storage.
    Returns bytes or None if storage/client is unavailable.
    """
    c = _get_client()
    if not c:
        return None
    try:
        res = c.storage.from_(bucket).download(path)
        # supabase-py may return bytes or a dict-like payload depending on version
        if isinstance(res, (bytes, bytearray)):
            return bytes(res)
        if isinstance(res, dict):
            data = res.get("data")
            if isinstance(data, (bytes, bytearray)):
                return bytes(data)
        return None
    except Exception:
        return None
