"""
PaddleOCR-only OCR service (bot + web).

IMPORTANT:
- No external OCR APIs are used here.
- PaddleOCR is initialized once via backend.services.paddle_ocr_runtime singleton.
"""

from __future__ import annotations

import asyncio
import html
import logging

from services.ocr_service import extract_text

logger = logging.getLogger(__name__)


async def extract_text_from_image(image_path: str) -> str:
    """
    Backward-compatible async API used by some web endpoints.

    Returns a small HTML snippet containing ONLY extracted text (no boxes/confidence).
    """
    try:
        lines = await asyncio.to_thread(extract_text, image_path)
        plain = "\n".join(lines or []).strip()
        if not plain:
            return ""
        return f'<div class="ocr-plain" style="white-space:pre-wrap">{html.escape(plain)}</div>'
    except Exception as e:
        logger.warning("Paddle OCR failed path=%s: %s", image_path, e, exc_info=True)
        return ""
