from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class OcrConfig:
    use_angle_cls: bool = True
    lang: str = "en"


_DEFAULT_CFG = OcrConfig(
    use_angle_cls=True,
    lang=(os.getenv("PADDLE_OCR_LANG", "en") or "en").strip() or "en",
)


def _clean_line(s: str) -> str:
    # Keep readable lines; normalize whitespace but don't over-normalize content.
    s = (s or "").replace("\r\n", "\n").replace("\r", "\n")
    s = " ".join(s.split())
    return s.strip()


def _iter_clean_lines(lines: Iterable[str]) -> list[str]:
    out: list[str] = []
    for raw in lines:
        c = _clean_line(str(raw))
        if not c:
            continue
        out.append(c)
    return out


def _normalize_to_supported_image_path(image_path: str) -> str:
    """
    Paddle/OpenCV can read many formats, but Telegram often sends WebP/HEIC.
    Convert to JPEG when needed so OCR is stable in production.
    """
    p = str(image_path)
    ext = os.path.splitext(p)[1].lower()
    if ext in {".jpg", ".jpeg", ".png"}:
        return p
    try:
        from PIL import Image
    except Exception:
        # If Pillow isn't available, best-effort: return original path.
        return p
    try:
        with Image.open(p) as im:
            im = im.convert("RGB")
            fd, out = tempfile.mkstemp(prefix="ocr_", suffix=".jpg")
            os.close(fd)
            im.save(out, "JPEG", quality=92, optimize=True)
            return out
    except Exception:
        return p


def extract_text(image_path: str, *, config: OcrConfig | None = None) -> list[str]:
    """
    Production OCR extraction (PaddleOCR only).

    Returns:
      Clean list of text lines in reading order.
    """
    if not image_path or not os.path.exists(str(image_path)):
        raise FileNotFoundError("Image not found")

    cfg = config or _DEFAULT_CFG
    tmp_converted: str | None = None
    try:
        normalized = _normalize_to_supported_image_path(str(image_path))
        if normalized != str(image_path):
            tmp_converted = normalized

        # Use the existing shared PaddleOCR singleton/runtime (thread-safe lazy init)
        from backend.services.paddle_ocr_runtime import (
            bytes_to_bgr,
            paddle_extract_structured,
            resize_for_ocr,
        )

        with open(normalized, "rb") as f:
            raw = f.read()
        bgr = bytes_to_bgr(raw)
        if bgr is None:
            raise ValueError("Invalid image data")

        bgr = resize_for_ocr(bgr)

        # We intentionally ignore boxes/confidence and only keep readable lines.
        structured = paddle_extract_structured(bgr, include_html_layout=False) or {}
        line_dicts = structured.get("lines") or []
        lines = [str(x.get("text") or "") for x in line_dicts if isinstance(x, dict)]
        cleaned = _iter_clean_lines(lines)

        # Fallback: sometimes `lines` can be empty but `text` has content
        if not cleaned:
            text = str(structured.get("text") or "").strip()
            if text:
                cleaned = _iter_clean_lines(text.splitlines())

        return cleaned
    finally:
        if tmp_converted:
            try:
                os.remove(tmp_converted)
            except Exception:
                pass

