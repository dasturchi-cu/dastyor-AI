"""Watermark configuration for preview / unpaid document exports."""

from __future__ import annotations

import os


def watermark_text() -> str:
    return (
        os.getenv("DOC_WATERMARK_TEXT")
        or "@DastyorAiBot"
    ).strip() or "@DastyorAiBot"


def watermark_opacity() -> float:
    try:
        v = float(os.getenv("DOC_WATERMARK_OPACITY", "0.08") or "0.08")
    except ValueError:
        v = 0.08
    return max(0.04, min(0.18, v))
