"""Watermark configuration for preview / unpaid document exports."""

from __future__ import annotations

import os


def _bot_handle() -> str:
    custom = (os.getenv("DOC_WATERMARK_TEXT") or "").strip()
    if custom:
        return custom
    try:
        from config.settings import settings

        uname = (settings.bot_username or "DastyorAiBot").lstrip("@")
    except Exception:
        uname = "DastyorAiBot"
    return f"@{uname}"


def watermark_text() -> str:
    """Tiled background watermark on preview / test PDF."""
    return _bot_handle()


def preview_banner_text() -> str:
    """Prominent top banner on demo/preview documents."""
    return (
        os.getenv("DOC_PREVIEW_BANNER_TEXT")
        or "DEMO — FAQAT KO'RISH UCHUN"
    ).strip() or "DEMO — FAQAT KO'RISH UCHUN"


def watermark_opacity() -> float:
    try:
        v = float(os.getenv("DOC_WATERMARK_OPACITY", "0.14") or "0.14")
    except ValueError:
        v = 0.14
    return max(0.06, min(0.24, v))
