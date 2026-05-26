"""Official document rendering utilities (Obyektivka / Ma'lumotnoma)."""

from bot.services.document_render.context import build_obyektivka_render_context
from bot.services.document_render.pii_mask import mask_text_for_preview
from bot.services.document_render.photo import process_passport_photo
from bot.services.document_render.watermark import watermark_text

__all__ = [
    "build_obyektivka_render_context",
    "mask_text_for_preview",
    "process_passport_photo",
    "watermark_text",
]
