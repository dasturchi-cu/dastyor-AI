"""Watermark configuration for preview / unpaid document exports."""

from __future__ import annotations

import os


def watermark_text() -> str:
    return (
        os.getenv("DOC_WATERMARK_TEXT")
        or os.getenv("PROJECT_NAME")
        or "DASTYOR AI"
    ).strip() or "DASTYOR AI"


def watermark_opacity() -> float:
    try:
        v = float(os.getenv("DOC_WATERMARK_OPACITY", "0.11") or "0.11")
    except ValueError:
        v = 0.11
    return max(0.04, min(0.25, v))
