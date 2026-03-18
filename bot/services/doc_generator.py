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
    """
    Best-effort DOCX -> PDF conversion.
    Tries (in order):
    - docx2pdf (Windows / Word)
    - LibreOffice (soffice) headless
    Returns PDF path or None.
    """
    if not docx_path or not os.path.exists(docx_path):
        return None
    os.makedirs(output_dir, exist_ok=True)

    base = os.path.splitext(os.path.basename(docx_path))[0]
    pdf_out = os.path.join(output_dir, f"{base}.pdf")

    # 1) docx2pdf
    try:
        from docx2pdf import convert  # type: ignore
        convert(docx_path, pdf_out)
        if os.path.exists(pdf_out):
            return pdf_out
    except Exception:
        pass

    # 2) LibreOffice (soffice)
    try:
        import subprocess
        cmd = [
            "soffice",
            "--headless",
            "--nologo",
            "--nolockcheck",
            "--nodefault",
            "--norestore",
            "--convert-to",
            "pdf",
            "--outdir",
            os.path.abspath(output_dir),
            os.path.abspath(docx_path),
        ]
        subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(pdf_out):
            return pdf_out
        # LibreOffice sometimes outputs with original name in same dir; accept any pdf with same base prefix
        for f in os.listdir(output_dir):
            if f.lower().endswith(".pdf") and os.path.splitext(f)[0] == base:
                return os.path.join(output_dir, f)
    except Exception:
        pass

    return None
