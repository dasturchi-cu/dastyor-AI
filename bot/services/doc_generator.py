"""
Document generator wrappers used by API handlers.
"""

import os
from typing import Any


def generate_obyektivka_docx(
    data: dict[str, Any],
    photo_path: str | None = None,
    output_dir: str = "temp",
) -> str:
    from bot.services.obyektivka_docx_official import generate_obyektivka_docx as _gen

    os.makedirs(output_dir, exist_ok=True)
    safe_name = (data.get("fullname") or "Obyektivka").replace(" ", "_").replace("/", "_")[:30] or "Obyektivka"
    filepath = os.path.join(output_dir, f"obyektivka_{safe_name}_@DastyorAiBot.docx")
    return _gen(user_data=data, photo_path=photo_path or "", output_filepath=filepath)


def generate_cv_docx(data: dict[str, Any], output_dir: str = "temp") -> str:
    from bot.keyboards.doc_generator import generate_cv_docx as _gen

    os.makedirs(output_dir, exist_ok=True)
    return _gen(data, output_dir=output_dir)


def convert_to_pdf_safe(docx_path: str, output_dir: str = "temp") -> str | None:
    return None
