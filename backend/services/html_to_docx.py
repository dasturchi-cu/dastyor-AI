"""HTML → DOCX via LibreOffice (preview shablon bilan bir xil layout)."""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from backend.services.docx_to_pdf import _find_soffice

logger = logging.getLogger(__name__)


def html_to_docx_bytes(html: str) -> bytes | None:
    """Render HTML string to DOCX bytes. Returns None if LibreOffice is unavailable."""
    soffice = _find_soffice()
    if not soffice:
        return None
    tmp = tempfile.mkdtemp(prefix="oby_html_docx_")
    try:
        html_path = Path(tmp) / "obyektivka.html"
        html_path.write_text(html, encoding="utf-8")
        subprocess.run(
            [
                soffice,
                "--headless",
                "--nologo",
                "--nofirststartwizard",
                "--convert-to",
                "docx",
                "--outdir",
                tmp,
                str(html_path),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        docx_path = Path(tmp) / "obyektivka.docx"
        if docx_path.is_file():
            return docx_path.read_bytes()
    except Exception as exc:
        logger.warning("LibreOffice HTML→DOCX failed: %s", exc)
        from shared.error_log import record_error

        record_error("docx", f"HTML→DOCX: {exc}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return None
