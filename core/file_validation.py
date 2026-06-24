"""Upload validation — magic bytes, size limits, light content scan."""
from __future__ import annotations

import io
import logging

from fastapi import HTTPException

from config.settings import settings

logger = logging.getLogger(__name__)

_IMAGE_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", "jpeg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"RIFF", "webp"),  # RIFF....WEBP
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
)

_AUDIO_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"OggS", "ogg"),
    (b"\xff\xfb", "mp3"),
    (b"\xff\xf3", "mp3"),
    (b"\xff\xf2", "mp3"),
    (b"ID3", "mp3"),
    (b"RIFF", "wav"),
    (b"fLaC", "flac"),
    (b"\x1a\x45\xdf\xa3", "webm"),
)


def _match_signature(data: bytes, signatures: tuple[tuple[bytes, str], ...]) -> str | None:
    if len(data) < 12:
        return None
    for sig, kind in signatures:
        if data.startswith(sig):
            if kind == "webp" and b"WEBP" not in data[:16]:
                continue
            if kind == "wav" and b"WAVE" not in data[:16]:
                continue
            return kind
    return None


def _scan_image_content(data: bytes) -> None:
    """PIL verify — rejects truncated or malformed images."""
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(data))
        img.verify()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Rasm fayli buzilgan yoki noto'g'ri") from exc


def validate_image_bytes(data: bytes, *, max_size: int | None = None) -> str:
    limit = max_size or settings.max_upload_image_bytes
    if not data:
        raise HTTPException(status_code=400, detail="Fayl bo'sh")
    if len(data) > limit:
        raise HTTPException(
            status_code=413,
            detail=f"Rasm hajmi {limit // (1024 * 1024)}MB dan oshmasligi kerak",
        )
    # Reject polyglot / script payloads in image uploads
    if b"<script" in data[:4096].lower() or b"<?php" in data[:4096].lower():
        raise HTTPException(status_code=400, detail="Rasm faylida xavfli kontent aniqlandi")
    kind = _match_signature(data, _IMAGE_SIGNATURES)
    if not kind:
        raise HTTPException(status_code=400, detail="Rasm formati qo'llab-quvvatlanmaydi (JPG/PNG/WebP)")
    _scan_image_content(data)
    return kind


def validate_audio_bytes(data: bytes, *, max_size: int | None = None) -> str:
    limit = max_size or settings.max_upload_audio_bytes
    if not data:
        raise HTTPException(status_code=400, detail="Audio bo'sh")
    if len(data) > limit:
        raise HTTPException(
            status_code=413,
            detail=f"Audio hajmi {limit // (1024 * 1024)}MB dan oshmasligi kerak",
        )
    kind = _match_signature(data, _AUDIO_SIGNATURES)
    if not kind:
        raise HTTPException(status_code=400, detail="Audio formati qo'llab-quvvatlanmaydi")
    return kind


def validate_text_length(text: str, *, max_len: int, field: str = "matn") -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail=f"{field} bo'sh")
    if len(cleaned) > max_len:
        raise HTTPException(status_code=400, detail=f"{field} juda uzun (max {max_len})")
    return cleaned
