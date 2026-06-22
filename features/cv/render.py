"""CV rendering — uses full render_service (WeasyPrint + PDF cache)."""
from __future__ import annotations

import asyncio
import logging

from backend.services.render_service import generate_cv_pdf as _generate_cv_pdf
from backend.services.render_service import render_cv_html

logger = logging.getLogger(__name__)


async def generate_cv_pdf(data: dict, base_url: str | None = None) -> bytes | None:
    """Render CV template → PDF bytes (cached WeasyPrint path in render_service)."""
    try:
        return await _generate_cv_pdf(data, base_url=base_url)
    except Exception as e:
        logger.error("CV PDF generation failed: %s", e)
        return None


def preview_html(data: dict) -> str:
    return render_cv_html(data)
