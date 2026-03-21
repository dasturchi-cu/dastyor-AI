from __future__ import annotations

from typing import Any

from backend.celery_app import celery_app
from backend.services.paddle_ocr_runtime import (
    ocr_extract_text_from_bytes,
    ocr_image_to_docx_from_bytes,
)


@celery_app.task(name="ocr.extract_text")
def ocr_extract_text(image_bytes: bytes) -> dict[str, Any]:
    return ocr_extract_text_from_bytes(image_bytes)


@celery_app.task(name="ocr.image_to_docx")
def ocr_image_to_docx(image_bytes: bytes) -> dict[str, Any]:
    return ocr_image_to_docx_from_bytes(image_bytes)
