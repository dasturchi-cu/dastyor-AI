"""Watermark configuration for preview / unpaid document exports."""

from __future__ import annotations

import os


def watermark_text() -> str:
    """Tiled background watermark on preview / test PDF."""
    return (
        os.getenv("DOC_WATERMARK_TEXT")
        or "DEMO VERSIYA · @DastyorAiBot"
    ).strip() or "DEMO VERSIYA · @DastyorAiBot"


def preview_banner_text() -> str:
    """Prominent top banner on demo/preview documents."""
    return (
        os.getenv("DOC_PREVIEW_BANNER_TEXT")
        or "DEMO VERSIYA — FAQAT KO'RISH UCHUN"
    ).strip() or "DEMO VERSIYA — FAQAT KO'RISH UCHUN"


def watermark_opacity() -> float:
    try:
        v = float(os.getenv("DOC_WATERMARK_OPACITY", "0.10") or "0.10")
    except ValueError:
        v = 0.10
    return max(0.04, min(0.22, v))
