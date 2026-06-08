"""Passport-style photo processing: white background, 3×4 crop."""

from __future__ import annotations

import base64
import io
import logging
import re

logger = logging.getLogger(__name__)

_DATA_URL = re.compile(r"^data:(image/[a-zA-Z0-9.+-]+);base64,(.+)$", re.S)


def process_passport_photo(data_url: str | None) -> str:
    """
    Normalize uploaded photo for official documents.
    - Flatten onto white background
    - Center-crop to 3:4
    - JPEG output for sharp PDF/print embedding
    """
    if not data_url or not isinstance(data_url, str):
        return data_url or ""

    m = _DATA_URL.match(data_url.strip())
    if not m:
        return data_url

    try:
        from PIL import Image, ImageOps
    except ImportError:
        logger.debug("Pillow not installed — photo passed through unchanged")
        return data_url

    mime, b64 = m.group(1), m.group(2)
    try:
        raw = base64.b64decode(b64)
        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA")

        w, h = img.size
        target_ratio = 3 / 4
        current_ratio = w / max(h, 1)

        if current_ratio > target_ratio:
            new_w = int(h * target_ratio)
            left = (w - new_w) // 2
            img = img.crop((left, 0, left + new_w, h))
        else:
            new_h = int(w / target_ratio)
            top = (h - new_h) // 2
            img = img.crop((0, top, w, top + new_h))

        if img.mode == "RGBA":
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg
        else:
            img = img.convert("RGB")

        out = io.BytesIO()
        img.save(out, format="JPEG", quality=92, optimize=True)
        encoded = base64.b64encode(out.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"
    except Exception as exc:
        logger.warning("Photo processing failed: %s", exc)
        return data_url


def compress_payload_photo(payload: dict, *, max_width: int = 480, quality: int = 85) -> dict:
    """Shrink base64 photo in API payloads before DB storage (faster saves/renders)."""
    if not isinstance(payload, dict):
        return payload
    out = dict(payload)
    for key in ("photo_data", "photo_base64", "img"):
        val = out.get(key)
        if not isinstance(val, str) or not val.startswith("data:image"):
            continue
        try:
            from PIL import Image, ImageOps

            m = _DATA_URL.match(val.strip())
            if not m:
                continue
            raw = base64.b64decode(m.group(2))
            img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
            w, h = img.size
            scale = min(1.0, max_width / max(w, 1))
            if scale < 1.0:
                img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)
            if img.mode == "RGBA":
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                img = bg
            else:
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            out[key] = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"
        except Exception as exc:
            logger.debug("compress_payload_photo skip %s: %s", key, exc)
    return out
