"""Convert DOCX → PDF for Obyektivka preview (no HTML)."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def _find_soffice() -> str | None:
    for name in ("soffice", "libreoffice", "loffice"):
        path = shutil.which(name)
        if path:
            return path
    for candidate in (
        Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
        Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
    ):
        if candidate.is_file():
            return str(candidate)
    return None


def _libreoffice_pdf(docx_path: Path, out_dir: Path) -> bytes | None:
    soffice = _find_soffice()
    if not soffice:
        return None
    try:
        subprocess.run(
            [
                soffice,
                "--headless",
                "--nologo",
                "--nofirststartwizard",
                "--convert-to",
                "pdf",
                "--outdir",
                str(out_dir),
                str(docx_path),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        pdf_path = out_dir / f"{docx_path.stem}.pdf"
        if pdf_path.is_file():
            return pdf_path.read_bytes()
    except Exception as exc:
        logger.warning("LibreOffice DOCX→PDF failed: %s", exc)
    return None


def _word_com_pdf(docx_path: Path, pdf_path: Path) -> bytes | None:
    if os.name != "nt":
        return None
    word = None
    doc = None
    try:
        import win32com.client  # type: ignore

        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(str(docx_path.resolve()), ReadOnly=True)
        doc.ExportAsFixedFormat(
            OutputFileName=str(pdf_path.resolve()),
            ExportFormat=17,
            OpenAfterExport=False,
            OptimizeFor=0,
            BitmapMissingFonts=True,
            DocStructureTags=False,
            CreateBookmarks=0,
            UseISO19005_1=False,
        )
        doc.Close(False)
        doc = None
        word.Quit()
        word = None
        time.sleep(0.3)
        if pdf_path.is_file():
            return pdf_path.read_bytes()
    except Exception as exc:
        logger.warning("Word COM DOCX→PDF failed: %s", exc)
    finally:
        if doc is not None:
            try:
                doc.Close(False)
            except Exception:
                pass
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass
    return None


def docx_bytes_to_pdf(docx_bytes: bytes) -> bytes:
    """DOCX bytes → PDF bytes via LibreOffice (production) or Word COM (Windows dev)."""
    tmp = tempfile.mkdtemp(prefix="oby_pdf_")
    try:
        docx_path = Path(tmp) / "obyektivka.docx"
        pdf_path = Path(tmp) / "obyektivka.pdf"
        docx_path.write_bytes(docx_bytes)

        pdf = _libreoffice_pdf(docx_path, Path(tmp))
        if pdf:
            return pdf

        pdf = _word_com_pdf(docx_path, pdf_path)
        if pdf:
            return pdf

        raise RuntimeError(
            "DOCX→PDF konvertatsiya mavjud emas. Production: LibreOffice. Windows: Microsoft Word."
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
