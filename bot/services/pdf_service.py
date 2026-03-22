"""
PDF generation service.

Takes a list of local image file paths and merges them into a single PDF.
Uses Pillow. Includes image compression for handling 20+ images efficiently.
"""

import os
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List

from PIL import Image

logger = logging.getLogger(__name__)

_pdf_img_executor = ThreadPoolExecutor(
    max_workers=min(24, max(8, (os.cpu_count() or 4) * 3)),
    thread_name_prefix="pdfimg",
)

# ── Compression settings ────────────────────────────────────────────────
# Katta rasmlar PDF ni sekin qiladi — env bilan boshqarish mumkin
MAX_DIMENSION = int(os.getenv("PDF_IMAGE_MAX_SIDE") or "1600")
JPEG_QUALITY = int(os.getenv("PDF_JPEG_QUALITY") or "80")
MAX_FILE_SIZE_MB = int(os.getenv("PDF_MAX_FILE_MB") or "12")


def _compress_image(img: Image.Image, max_side: int) -> Image.Image:
    """
    Resize and compress an image for PDF embedding.
    - Converts to RGB (required for PDF)
    - Resizes if any dimension exceeds max_side
    """
    img = img.convert("RGB")
    w, h = img.size
    cap = int(max_side)
    if w > cap or h > cap:
        ratio = min(cap / w, cap / h)
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        logger.debug("Resized image from %sx%s to %sx%s", w, h, new_w, new_h)

    return img


def _open_compress_pair(args: tuple[str, int]) -> Image.Image | None:
    path, max_side = args
    try:
        file_size_mb = os.path.getsize(path) / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            logger.warning("Skipping %s: %.1f MB exceeds limit", path, file_size_mb)
            return None
        with Image.open(path) as raw:
            return _compress_image(raw, max_side)
    except Exception as e:
        logger.warning("Failed to process image %s: %s", path, e)
        return None


def images_to_pdf(
    image_paths: List[str],
    output_path: str,
    *,
    max_dimension: int | None = None,
    pdf_resolution: float | None = None,
) -> str:
    """
    Merge multiple images into a single PDF with compression.
    max_dimension: None = env PDF_IMAGE_MAX_SIDE (bot); web uchun kichikroq qiymat tezroq PDF.
    pdf_resolution: Pillow PDF resolution (default 100); 72–90 tezroq/yengil.
    """
    if not image_paths:
        raise ValueError("image_paths bo'sh bo'lishi mumkin emas")

    cap = int(max_dimension) if max_dimension is not None else MAX_DIMENSION
    res = float(pdf_resolution) if pdf_resolution is not None else 100.0
    pairs = [(p, cap) for p in image_paths]
    pil_images = [
        im for im in _pdf_img_executor.map(_open_compress_pair, pairs) if im is not None
    ]

    if not pil_images:
        raise ValueError("Yaroqli rasmlar topilmadi.")

    first, *rest = pil_images
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    first.save(
        output_path,
        "PDF",
        resolution=res,
        save_all=True,
        append_images=rest,
    )

    # Free memory immediately
    for img in pil_images:
        try:
            img.close()
        except Exception:
            pass

    logger.info(f"PDF created: {len(pil_images)} images → {output_path}")
    return output_path
