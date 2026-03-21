"""
Shared synchronous PaddleOCR pipeline for:
- FastAPI handlers (via asyncio.run_in_executor + shared pool)
- Celery workers (same code path = no drift)

GPU: set PADDLE_OCR_USE_GPU=1 if Paddle build supports CUDA (optional).
"""
from __future__ import annotations

import base64
import io
import inspect
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

os.environ.setdefault("FLAGS_enable_pir_api", "0")
os.environ.setdefault("FLAGS_use_new_executor", "0")
os.environ.setdefault("FLAGS_enable_onednn", "0")
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_enable_pir_in_executor", "0")

logger = logging.getLogger("dastyor.paddle_ocr")

_OCR_POOL = ThreadPoolExecutor(max_workers=int(os.getenv("OCR_WORKERS", "4")), thread_name_prefix="paddle")
_OCR_ENGINE = None
_OCR_LOCK = threading.Lock()
_OCR_PROFILE = "default"


def get_ocr_thread_pool() -> ThreadPoolExecutor:
    return _OCR_POOL


def _runtime_executor_error(exc: Exception) -> bool:
    msg = str(exc)
    return "ConvertPirAttribute2RuntimeAttribute" in msg or "onednn_instruction.cc" in msg


def _filter_paddle_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    try:
        from paddleocr import PaddleOCR

        sig = inspect.signature(PaddleOCR)
        return {k: v for k, v in kwargs.items() if k in sig.parameters}
    except Exception:
        return kwargs


def _build_paddle_kwargs(profile: str) -> dict[str, Any]:
    lang = os.getenv("PADDLE_OCR_LANG", "en")
    det_limit = int(os.getenv("PADDLE_OCR_DET_LIMIT_SIDE_LEN", "1800"))
    kwargs: dict[str, Any] = {
        "lang": lang,
        "use_angle_cls": True,
        "show_log": False,
        "det_limit_side_len": det_limit,
        "enable_mkldnn": False,
    }
    if profile == "fallback_v4":
        kwargs["ocr_version"] = os.getenv("PADDLE_OCR_FALLBACK_VERSION", "PP-OCRv4")
    else:
        kwargs["ocr_version"] = os.getenv("PADDLE_OCR_VERSION", "PP-OCRv4")
    if os.getenv("PADDLE_OCR_USE_GPU", "").lower() in ("1", "true", "yes"):
        kwargs["use_gpu"] = True
    return _filter_paddle_kwargs(kwargs)


def _init_paddle_engine(profile: str):
    global _OCR_ENGINE, _OCR_PROFILE
    from paddleocr import PaddleOCR

    try:
        import paddle

        paddle.set_flags(
            {
                "FLAGS_enable_pir_api": False,
                "FLAGS_use_new_executor": False,
                "FLAGS_enable_onednn": False,
                "FLAGS_use_mkldnn": False,
                "FLAGS_enable_pir_in_executor": False,
            }
        )
    except Exception:
        pass

    filtered = _build_paddle_kwargs(profile)
    try:
        _OCR_ENGINE = PaddleOCR(**filtered)
    except TypeError as e:
        if "unexpected keyword argument" in str(e):
            _OCR_ENGINE = PaddleOCR(
                lang=os.getenv("PADDLE_OCR_LANG", "en"),
                use_angle_cls=True,
                show_log=False,
            )
        else:
            raise
    _OCR_PROFILE = profile
    logger.info("PaddleOCR initialized profile=%s", profile)


def get_paddle_engine():
    """Lazy-init PaddleOCR (thread-safe); tries default then PP-OCRv4 fallback."""
    global _OCR_ENGINE
    if _OCR_ENGINE is not None:
        return _OCR_ENGINE
    with _OCR_LOCK:
        if _OCR_ENGINE is not None:
            return _OCR_ENGINE
        last_err: Exception | None = None
        for profile in ("default", "fallback_v4"):
            try:
                _init_paddle_engine(profile)
                return _OCR_ENGINE
            except Exception as e:
                last_err = e
                _OCR_ENGINE = None
                continue
        raise RuntimeError(f"PaddleOCR init failed: {last_err}")


def reinit_paddle_engine_fallback():
    """After runtime/oneDNN crashes, force PP-OCRv4 profile."""
    global _OCR_ENGINE
    with _OCR_LOCK:
        _OCR_ENGINE = None
        _init_paddle_engine("fallback_v4")


def ensure_paddle_imports():
    """Raise ImportError if numpy/cv2/paddleocr missing."""
    import numpy as np  # noqa: F401
    import cv2  # noqa: F401
    from paddleocr import PaddleOCR  # noqa: F401


def bytes_to_bgr(image_bytes: bytes):
    import numpy as np
    import cv2

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def resize_for_ocr(bgr, max_side: int | None = None):
    import cv2

    ms = max_side if max_side is not None else int(os.getenv("PADDLE_OCR_MAX_SIDE", "1800"))
    try:
        h, w = bgr.shape[:2]
        m = max(h, w)
        if m <= ms:
            return bgr
        scale = ms / float(m)
        nh = max(1, int(round(h * scale)))
        nw = max(1, int(round(w * scale)))
        return cv2.resize(bgr, (nw, nh), interpolation=cv2.INTER_AREA)
    except Exception:
        return bgr


def cv_preprocess(bgr):
    import cv2
    import numpy as np

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    equalized = cv2.equalizeHist(gray)
    denoised = cv2.GaussianBlur(equalized, (3, 3), 0)
    binary = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        15,
    )
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
    return cv2.filter2D(binary, -1, kernel)


def paddle_extract_plain_text(processed) -> str:
    import cv2

    img = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR) if len(processed.shape) == 2 else processed
    try:
        engine = get_paddle_engine()
        result = engine.ocr(img) or []
    except Exception as e:
        if _runtime_executor_error(e):
            logger.warning("Paddle runtime executor issue; reinitializing with fallback profile")
            reinit_paddle_engine_fallback()
            result = get_paddle_engine().ocr(img) or []
        else:
            raise
    lines: list[str] = []
    for block in result:
        for item in block or []:
            try:
                t = item[1][0]
            except Exception:
                t = ""
            if t:
                lines.append(str(t).strip())
    return "\n".join(lines).strip()


def docx_image_then_text(image_bytes: bytes, text: str) -> bytes:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches

    doc = Document()
    try:
        sec = doc.sections[0]
        sec.top_margin = Inches(0.4)
        sec.bottom_margin = Inches(0.4)
        sec.left_margin = Inches(0.4)
        sec.right_margin = Inches(0.4)
    except Exception:
        pass

    bio = io.BytesIO(image_bytes)
    bio.name = "upload.jpg"
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(bio, width=Inches(7.2))
    doc.add_page_break()
    for line in (text or "").splitlines():
        doc.add_paragraph(line)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


def ocr_extract_text_from_bytes(image_bytes: bytes) -> dict[str, Any]:
    img = bytes_to_bgr(image_bytes)
    if img is None:
        raise ValueError("Invalid image")
    img = resize_for_ocr(img)
    processed = cv_preprocess(img)
    text = paddle_extract_plain_text(processed)
    return {"text": text}


def ocr_image_to_docx_from_bytes(image_bytes: bytes) -> dict[str, Any]:
    img = bytes_to_bgr(image_bytes)
    if img is None:
        raise ValueError("Invalid image")
    img = resize_for_ocr(img)
    processed = cv_preprocess(img)
    try:
        text = paddle_extract_plain_text(processed)
    except Exception as e:
        logger.warning("Paddle OCR failed, image-only DOCX: %s", e)
        text = ""
    docx_bytes = docx_image_then_text(image_bytes, text)
    return {"docx_b64": base64.b64encode(docx_bytes).decode("ascii"), "text": text}
