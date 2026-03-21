"""Extract plain text from uploaded document bytes (WebApp spellcheck, APIs)."""
from __future__ import annotations

import io
import logging
from typing import Final

logger = logging.getLogger(__name__)

_SUPPORTED: Final = frozenset({"txt", "docx", "pptx", "pdf"})


def extract_plain_text_from_bytes(filename: str, raw: bytes) -> str:
    if not raw:
        raise ValueError("Empty file")
    ext = (filename or "").rsplit(".", 1)[-1].lower()
    if ext not in _SUPPORTED:
        raise ValueError(f"Unsupported type .{ext}; use .txt, .docx, .pptx, .pdf")

    if ext == "txt":
        for enc in ("utf-8", "utf-8-sig", "cp1251", "latin-1"):
            try:
                return raw.decode(enc)
            except Exception:
                continue
        return raw.decode("utf-8", errors="replace")

    if ext == "docx":
        from docx import Document

        doc = Document(io.BytesIO(raw))
        parts = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    parts.append("\t".join(cells))
        return "\n".join(parts)

    if ext == "pptx":
        from pptx import Presentation

        prs = Presentation(io.BytesIO(raw))
        parts: list[str] = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    parts.append(shape.text.strip())
        return "\n".join(parts)

    if ext == "pdf":
        try:
            from pypdf import PdfReader
        except ImportError as e:
            logger.error("pypdf missing for PDF text extract: %s", e)
            raise ValueError("PDF imlo uchun serverda pypdf kutubxonasi kerak") from e
        reader = PdfReader(io.BytesIO(raw))
        texts: list[str] = []
        for page in reader.pages:
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            if t.strip():
                texts.append(t)
        return "\n".join(texts).strip()

    raise ValueError("Unsupported format")
