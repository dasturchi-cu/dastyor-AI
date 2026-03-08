"""
PDF generation service.

Takes a list of local image file paths and merges them into a single PDF.
Uses Pillow. Includes image compression for handling 20+ images efficiently.
"""

import os
import logging
from typing import List

from PIL import Image

logger = logging.getLogger(__name__)

# ── Compression settings ────────────────────────────────────────────────
MAX_DIMENSION = 1920       # Max width or height in pixels
JPEG_QUALITY = 82          # JPEG quality (1-100) for compressed images
MAX_FILE_SIZE_MB = 10      # Skip images larger than this


def _compress_image(img: Image.Image) -> Image.Image:
    """
    Resize and compress an image for PDF embedding.
    - Converts to RGB (required for PDF)
    - Resizes if any dimension exceeds MAX_DIMENSION
    - Returns the processed image
    """
    # Force RGB
    img = img.convert("RGB")

    # Resize if too large
    w, h = img.size
    if w > MAX_DIMENSION or h > MAX_DIMENSION:
        ratio = min(MAX_DIMENSION / w, MAX_DIMENSION / h)
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        logger.debug(f"Resized image from {w}x{h} to {new_w}x{new_h}")

    return img


def images_to_pdf(image_paths: List[str], output_path: str) -> str:
    """
    Merge multiple images into a single PDF with compression.

    :param image_paths: List of image file paths
    :param output_path: Destination PDF path
    :return: The PDF file path
    """
    if not image_paths:
        raise ValueError("image_paths bo'sh bo'lishi mumkin emas")

    pil_images = []
    for path in image_paths:
        try:
            # Skip files that are too large
            file_size_mb = os.path.getsize(path) / (1024 * 1024)
            if file_size_mb > MAX_FILE_SIZE_MB:
                logger.warning(f"Skipping {path}: {file_size_mb:.1f} MB exceeds limit")
                continue

            img = Image.open(path)
            img = _compress_image(img)
            pil_images.append(img)
        except Exception as e:
            logger.warning(f"Failed to process image {path}: {e}")

    if not pil_images:
        raise ValueError("Yaroqli rasmlar topilmadi.")

    first, *rest = pil_images
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    first.save(
        output_path,
        "PDF",
        resolution=100.0,
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
