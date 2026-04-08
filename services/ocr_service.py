from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class OcrConfig:
    use_angle_cls: bool = True
    lang: str = "en"
    upscale: float = 1.0
    enhance: bool = True


_DEFAULT_CFG = OcrConfig(
    use_angle_cls=True,
    lang=(os.getenv("PADDLE_OCR_LANG", "en") or "en").strip() or "en",
    upscale=float(os.getenv("OCR_UPSCALE", "1.0") or "1.0"),
    enhance=(os.getenv("OCR_ENHANCE_IMAGE", "1").strip().lower() not in {"0", "false", "no", "off"}),
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
    Also applies EXIF orientation (Telegram/phone photos).
    """
    p = str(image_path)
    ext = os.path.splitext(p)[1].lower()
    if ext in {".jpg", ".jpeg", ".png"}:
        # Still try to normalize EXIF orientation into a clean JPEG (cheap, avoids sideways text).
        try:
            from PIL import Image, ImageOps

            with Image.open(p) as im:
                im = ImageOps.exif_transpose(im).convert("RGB")
                fd, out = tempfile.mkstemp(prefix="ocr_", suffix=".jpg")
                os.close(fd)
                im.save(out, "JPEG", quality=92, optimize=True)
                return out
        except Exception:
            return p
    try:
        from PIL import Image, ImageOps
    except Exception:
        # If Pillow isn't available, best-effort: return original path.
        return p
    try:
        with Image.open(p) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            fd, out = tempfile.mkstemp(prefix="ocr_", suffix=".jpg")
            os.close(fd)
            im.save(out, "JPEG", quality=92, optimize=True)
            return out
    except Exception:
        return p


def _enhance_image_for_ocr(src_path: str, *, upscale: float = 1.0) -> str | None:
    """
    Best-effort enhancement for blurry/low-contrast scans.
    Produces a temporary JPEG for OCR.
    """
    try:
        from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    except Exception:
        return None
    try:
        with Image.open(src_path) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            sc = float(upscale or 1.0)
            sc = max(1.0, min(3.0, sc))
            if sc > 1.02:
                w, h = im.size
                im = im.resize((max(1, int(w * sc)), max(1, int(h * sc))), Image.Resampling.LANCZOS)
            # Contrast/clarity for faint tables
            im = ImageOps.autocontrast(im, cutoff=1)
            im = ImageEnhance.Contrast(im).enhance(1.65)
            im = ImageEnhance.Sharpness(im).enhance(1.4)
            # Mild edge sharpening (helps grid lines/text separation)
            im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=180, threshold=2))
            fd, out = tempfile.mkstemp(prefix="ocr_enh_", suffix=".jpg")
            os.close(fd)
            im.save(out, "JPEG", quality=92, optimize=True)
            return out
    except Exception:
        return None


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
    tmp_enhanced: str | None = None
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

        def _run_once(path: str) -> list[str]:
            with open(path, "rb") as f:
                raw = f.read()
            bgr = bytes_to_bgr(raw)
            if bgr is None:
                raise ValueError("Invalid image data")
            bgr = resize_for_ocr(bgr)
            structured = paddle_extract_structured(bgr, include_html_layout=False) or {}
            line_dicts = structured.get("lines") or []
            lines = [str(x.get("text") or "") for x in line_dicts if isinstance(x, dict)]
            cleaned_local = _iter_clean_lines(lines)
            if not cleaned_local:
                text = str(structured.get("text") or "").strip()
                if text:
                    cleaned_local = _iter_clean_lines(text.splitlines())
            return cleaned_local

        cleaned = _run_once(normalized)

        # If still empty, retry with 90° rotation (common for scanned tables/photos).
        if not cleaned:
            try:
                from PIL import Image

                with Image.open(normalized) as im:
                    im = im.convert("RGB")
                    fd, rot_path = tempfile.mkstemp(prefix="ocr_rot_", suffix=".jpg")
                    os.close(fd)
                    im.rotate(90, expand=True).save(rot_path, "JPEG", quality=92, optimize=True)
                try:
                    cleaned = _run_once(rot_path)
                finally:
                    try:
                        os.remove(rot_path)
                    except Exception:
                        pass
            except Exception:
                pass

        # If still empty, enhance (upscale/contrast/sharpen) and retry (plus 270° rotate).
        if not cleaned and cfg.enhance:
            tmp_enhanced = _enhance_image_for_ocr(normalized, upscale=cfg.upscale)
            if tmp_enhanced and os.path.exists(tmp_enhanced):
                cleaned = _run_once(tmp_enhanced)
                if not cleaned:
                    try:
                        from PIL import Image

                        with Image.open(tmp_enhanced) as im:
                            im = im.convert("RGB")
                            fd, rot2 = tempfile.mkstemp(prefix="ocr_rot2_", suffix=".jpg")
                            os.close(fd)
                            im.rotate(270, expand=True).save(rot2, "JPEG", quality=92, optimize=True)
                        try:
                            cleaned = _run_once(rot2)
                        finally:
                            try:
                                os.remove(rot2)
                            except Exception:
                                pass
                    except Exception:
                        pass

        return cleaned
    finally:
        if tmp_enhanced:
            try:
                os.remove(tmp_enhanced)
            except Exception:
                pass
        if tmp_converted:
            try:
                os.remove(tmp_converted)
            except Exception:
                pass

