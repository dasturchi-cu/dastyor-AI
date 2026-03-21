"""Central upload size checks (aligned with backend.settings)."""
from __future__ import annotations

from fastapi import UploadFile

from backend.settings import get_settings


class UploadTooLargeError(ValueError):
    pass


class EmptyUploadError(ValueError):
    pass


async def read_upload_limited(file: UploadFile, max_bytes: int | None = None) -> bytes:
    limit = max_bytes if max_bytes is not None else get_settings().max_upload_bytes
    raw = await file.read()
    if not raw:
        raise EmptyUploadError("Empty file")
    if len(raw) > limit:
        raise UploadTooLargeError(f"File too large (max {limit} bytes)")
    return raw
