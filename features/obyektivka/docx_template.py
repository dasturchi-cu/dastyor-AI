"""Generate Obyektivka DOCX from master template — layout clone + placeholder replace only."""

from __future__ import annotations

import base64
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from docx import Document
from docx.shared import Cm
from docxtpl import DocxTemplate

from backend.services.document_render.photo import process_passport_photo
from config.settings import TEMPLATES_DIR
from features.obyektivka.docx_picture import add_floating_picture
from features.obyektivka.placeholders import build_placeholder_context

logger = logging.getLogger(__name__)

MASTER_TEMPLATE = TEMPLATES_DIR / "obyektivka_master.docx"


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _decode_photo_data(data: dict[str, Any]) -> str | None:
    photo_data = _to_text(data.get("photo_data") or data.get("img"))
    if not photo_data.startswith("data:image/") or "," not in photo_data:
        return None
    try:
        photo_data = process_passport_photo(photo_data)
        header, b64 = photo_data.split(",", 1)
        mime = header.split(";")[0].split(":")[1].lower()
        ext = {"image/png": "png", "image/jpeg": "jpg", "image/jpg": "jpg", "image/webp": "webp"}.get(mime, "jpg")
        os.makedirs("temp", exist_ok=True)
        path = os.path.join("temp", f"oby_tpl_photo_{os.getpid()}.{ext}")
        with open(path, "wb") as fh:
            fh.write(base64.b64decode(b64))
        return path
    except Exception as exc:
        logger.warning("photo_data decode failed: %s", exc)
        return None


def _inject_photo(doc: Document, photo_path: str) -> None:
    """Insert uploaded photo into header without changing template structure."""
    if not photo_path or not os.path.isfile(photo_path):
        return
    target = None
    for p in doc.paragraphs[:4]:
        if "MA" in (p.text or "").upper() and "LUMOT" in (p.text or "").upper():
            target = p
            break
    if target is None and doc.paragraphs:
        target = doc.paragraphs[0]
    if target is None:
        return
    add_floating_picture(target, photo_path, width=Cm(3), height=Cm(4))


def _clear_photo_hint_marker(doc: Document) -> None:
    for p in doc.paragraphs:
        for run in p.runs:
            if "{{photo}}" in run.text:
                run.text = run.text.replace("{{photo}}", "")


def generate_obyektivka_docx(
    user_data: dict[str, Any] | None = None,
    photo_path: str | None = None,
    output_filepath: str | None = None,
    **kwargs: Any,
) -> str:
    """
    Master template → placeholder replace → DOCX.
    Layout/styles come only from templates/obyektivka_master.docx (reference clone).
    """
    data = user_data or kwargs.get("data") or {}
    if not isinstance(data, dict):
        raise ValueError("user_data must be a dictionary")

    if not MASTER_TEMPLATE.is_file():
        raise FileNotFoundError(
            f"Master template missing: {MASTER_TEMPLATE}. Run scripts/build_obyektivka_master.py"
        )

    temp_photo: str | None = None
    if not photo_path or not os.path.exists(photo_path):
        temp_photo = _decode_photo_data(data)

    resolved_photo = photo_path if photo_path and os.path.exists(photo_path) else temp_photo

    if not output_filepath:
        os.makedirs("temp", exist_ok=True)
        safe = (_to_text(data.get("fullname")) or "Obyektivka").replace(" ", "_").replace("/", "_")
        output_filepath = os.path.join("temp", f"obyektivka_{safe}_{os.getpid()}.docx")
    else:
        os.makedirs(os.path.dirname(output_filepath) or ".", exist_ok=True)

    ctx = build_placeholder_context(data)
    tpl = DocxTemplate(str(MASTER_TEMPLATE))
    tpl.render(ctx)

    if resolved_photo:
        doc = tpl.docx
        _inject_photo(doc, resolved_photo)
        _clear_photo_hint_marker(doc)
        tpl.save(output_filepath)
    else:
        tpl.save(output_filepath)

    if temp_photo:
        try:
            os.remove(temp_photo)
        except OSError:
            pass

    return output_filepath


def generate_obyektivka_docx_bytes(data: dict[str, Any], *, photo_path: str | None = None) -> bytes:
    path = generate_obyektivka_docx(data, photo_path=photo_path)
    try:
        return Path(path).read_bytes()
    finally:
        try:
            Path(path).unlink(missing_ok=True)
        except OSError:
            pass
