"""
OCR Service Module (Async Optimized)
Handles Image-to-Text conversion using Gemini asynchronously to prevent blocking.
Uses a dedicated thread pool so OCR never blocks other bot features.
"""
import logging
import asyncio
import os
import re
import tempfile
import time
import warnings
from concurrent.futures import ThreadPoolExecutor

warnings.filterwarnings(
    "ignore",
    message=".*google.generativeai.*",
    category=DeprecationWarning,
)

import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold, HarmCategory
from PIL import Image

from config import GOOGLE_API_KEY

logger = logging.getLogger(__name__)

# Dedicated thread pool for OCR tasks — prevents blocking other bot features
_ocr_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ocr")

# OCR timeout (seconds) — prevents the bot from hanging on slow Gemini responses
OCR_TIMEOUT = 120

# Hujjat OCR uchun — Gemini tez-tez xavfsizlik bilan bo'sh javob qaytaradi
_OCR_SAFETY = [
    {"category": HarmCategory.HARM_CATEGORY_HARASSMENT, "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH},
    {"category": HarmCategory.HARM_CATEGORY_HATE_SPEECH, "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH},
    {"category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH},
    {"category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH},
]


def _extract_text_from_gemini_response(result) -> str:
    """result.text ba'zan bo'sh yoki xato; parts va finish_reason ni ham tekshiramiz."""
    if not result:
        return ""
    try:
        t = (result.text or "").strip()
        if t:
            return t
    except Exception as e:
        logger.warning("Gemini result.text o'qilmadi: %s", e)
    try:
        for c in getattr(result, "candidates", None) or []:
            content = getattr(c, "content", None)
            if not content:
                fr = getattr(c, "finish_reason", None)
                logger.info("Gemini: content yo'q, finish_reason=%s", fr)
                continue
            parts = getattr(content, "parts", None) or []
            chunks = [p.text for p in parts if getattr(p, "text", None)]
            if chunks:
                return "".join(chunks).strip()
            fr = getattr(c, "finish_reason", None)
            logger.info("Gemini: parts matnsiz, finish_reason=%s", fr)
    except Exception as e:
        logger.warning("Gemini parts ajratish xato: %s", e)
    try:
        pf = getattr(result, "prompt_feedback", None)
        if pf is not None:
            logger.info("Gemini prompt_feedback=%s block_reason=%s", pf, getattr(pf, "block_reason", None))
    except Exception:
        pass
    return ""


def _blocking_upload_path(path: str):
    try:
        myfile = genai.upload_file(path)
        waited = 0
        while myfile.state.name == "PROCESSING" and waited < 30:
            time.sleep(1)
            waited += 1
            try:
                myfile = genai.get_file(myfile.name)
            except Exception:
                break
        return myfile
    except Exception as e:
        logger.error("OCR upload failed: %s", e)
        return None


def _normalize_image_to_png_sync(src_path: str) -> str | None:
    """Telegram/WebP/RGBA va noto'g'ri kengaytma uchun bitta PNG."""
    try:
        with Image.open(src_path) as im:
            im = im.convert("RGB")
            fd, out = tempfile.mkstemp(suffix=".png", prefix="ocr_norm_")
            os.close(fd)
            im.save(out, "PNG", optimize=True)
            return out
    except Exception as e:
        logger.warning("OCR PNG normalize failed %s: %s", src_path, e)
        return None


def _enhance_image_for_ocr_sync(src_path: str) -> str | None:
    """
    Improve OCR accuracy by enhancing contrast/sharpness and upscaling.
    This helps Gemini read faint lines, stamps, and small text.
    """
    try:
        from PIL import ImageEnhance, ImageFilter, ImageOps
    except Exception:
        return None
    try:
        with Image.open(src_path) as im:
            im = im.convert("RGB")
            # Upscale (keeps small fonts readable)
            try:
                scale = float(os.getenv("OCR_UPSCALE", "1.8") or "1.8")
            except Exception:
                scale = 1.8
            scale = max(1.0, min(3.0, scale))
            if scale > 1.01:
                w, h = im.size
                im = im.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
            # Auto-contrast and slight brightness boost
            im = ImageOps.autocontrast(im, cutoff=1)
            im = ImageEnhance.Contrast(im).enhance(1.55)
            im = ImageEnhance.Brightness(im).enhance(1.06)
            # Mild denoise then sharpen edges / lines
            im = im.filter(ImageFilter.MedianFilter(size=3))
            im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=190, threshold=2))

            # Optional: binarize for handwriting/ledger tables (often improves digits)
            bin_on = os.getenv("OCR_BINARIZE", "1").strip().lower() not in {"0", "false", "no", "off"}
            if bin_on:
                g = ImageOps.grayscale(im)
                # Adaptive-ish threshold (fast): use histogram percentile
                hist = g.histogram()
                total = sum(hist) or 1
                acc = 0
                thr = 160
                target = int(total * 0.62)
                for i, v in enumerate(hist):
                    acc += v
                    if acc >= target:
                        thr = i
                        break
                thr = max(90, min(200, int(thr)))
                bw = g.point(lambda p: 255 if p > thr else 0, mode="1")
                im = bw.convert("RGB")
            fd, out = tempfile.mkstemp(suffix=".png", prefix="ocr_enh_")
            os.close(fd)
            im.save(out, "PNG", optimize=True)
            return out
    except Exception as e:
        logger.info("OCR enhance skipped %s: %s", src_path, e)
        return None


def _extract_layout_with_paddle_sync(image_path: str) -> str:
    """Best-effort: local Paddle layout HTML for stronger 1:1 numbering/placement."""
    try:
        from backend.services.paddle_ocr_runtime import ocr_extract_text_from_bytes
    except Exception:
        return ""
    try:
        with open(image_path, "rb") as f:
            raw = f.read()
        out = ocr_extract_text_from_bytes(raw) or {}
        return str(out.get("html_layout") or "").strip()
    except Exception as e:
        logger.info("Paddle layout OCR unavailable/fail path=%s: %s", image_path, e)
        return ""


def _layout_html_quality_ok(layout_html: str) -> bool:
    """
    Heuristic gate:
    - Agar savolnoma/list hujjatda raqamlar tushib qolsa, Paddle layoutni rad etib Gemini'ga o'tamiz.
    """
    h = (layout_html or "").strip()
    if len(h) < 80:
        return False
    txt = re.sub(r"<[^>]+>", " ", h)
    txt = re.sub(r"\s+", " ", txt).strip()
    if len(txt) < 40:
        return False
    qmarks = txt.count("?")
    numbered = len(re.findall(r"\b\d{1,2}\.\s", txt))
    if qmarks >= 4 and numbered <= 1:
        return False
    return True


async def extract_text_from_image(image_path: str) -> str:
    """
    Extracts text from an image file using Gemini asynchronously.
    Forces 1:1 HTML layout preservation. Does not block the event loop.
    """
    if not GOOGLE_API_KEY:
        return ""

    t0 = time.perf_counter()
    norm_png: str | None = None
    upload_from_norm_only = False
    try:
        logger.info("OCR extract started path=%s", image_path)

        loop = asyncio.get_running_loop()
        # Default OFF: Paddle layout often doesn't map 1:1 into DOCX (absolute divs stretch).
        prefer_paddle_layout = os.getenv("OCR_BOT_PREFER_PADDLE_LAYOUT", "0").strip().lower() not in {
            "0", "false", "no", "off",
        }
        if prefer_paddle_layout:
            paddle_html = await loop.run_in_executor(
                _ocr_executor, _extract_layout_with_paddle_sync, image_path
            )
            if paddle_html and _layout_html_quality_ok(paddle_html):
                logger.info("OCR done via Paddle layout in %.1fs path=%s", time.perf_counter() - t0, image_path)
                return paddle_html
            if paddle_html:
                logger.info("Paddle layout quality low, fallback to Gemini path=%s", image_path)

        # Enhance image for OCR (optional but ON by default)
        enhance_on = os.getenv("OCR_ENHANCE_IMAGE", "1").strip().lower() not in {"0", "false", "no", "off"}
        upload_path = image_path
        enh_png: str | None = None
        if enhance_on:
            enh_png = await loop.run_in_executor(_ocr_executor, _enhance_image_for_ocr_sync, image_path)
            if enh_png and os.path.exists(enh_png):
                upload_path = enh_png

        myfile = await loop.run_in_executor(_ocr_executor, _blocking_upload_path, upload_path)
        if not myfile or myfile.state.name == "FAILED":
            logger.warning("Gemini upload as-is failed, trying PNG normalize path=%s", image_path)
            myfile = None

        if not myfile:
            norm_png = await loop.run_in_executor(_ocr_executor, _normalize_image_to_png_sync, image_path)
            if norm_png:
                myfile = await loop.run_in_executor(_ocr_executor, _blocking_upload_path, norm_png)
                if myfile and myfile.state.name != "FAILED":
                    upload_from_norm_only = True
            if not myfile or myfile.state.name == "FAILED":
                logger.error("Gemini file upload/processing failed (incl. PNG retry).")
                return ""

        # Use fallback model list — don't hardcode a single model
        from bot.services.ai_service import get_model
        model = await get_model()
        if not model:
            logger.error("No Gemini model available for OCR.")
            return ""

        prompt = """You are an advanced OCR AI specialized in EXTREME 1:1 Document Replication.
Your task is to convert the provided image into a structured HTML document that EXACTLY matches the original layout, formatting, and text, no matter how blurry, faded, or complex the image is.

CRITICAL RULES FOR 1:1 REPLICATION:
1. **Absolute Text Accuracy**: DO NOT hallucinate, summarize, or fix grammar. Extract every single word, number, punctuation mark, and character exactly as it appears. If text is blurry or hard to read, make your absolute best logical guess based on context, but NEVER skip it. Keep the original language.
2. **Typography & Styling**: Use <b>/<strong> for bold, <i>/<em> for italics, <u> for underlines. If text is entirely uppercase in the image, output it in uppercase.
3. **Alignment & Positioning**: Use <p align="center">, <p align="right">, <p align="justify">, or <h1 align="center">. Use standard html alignment attributes or inline styles like style="text-align: right" for any content that is centered, right-aligned, or justified.
4. **Tables & Grids**: If you see ANY tabular data, grids, columns, side-by-side text, or form fields, ALWAYS use HTML <table>. Ensure the exact number of rows and columns. Never use tabs or spaces for spacing. Set approximate column widths on the first row: <td width="30%">. Empty cells must remain empty (<td></td>).
5. **Structure**: Use <h1>, <h2>, <h3> for titles and headings based on their visual size. Use <p> for regular text paragraphs. Use <ul>, <ol>, <li> for lists.
6. **Spacing & Gaps**: Use <br> to preserve exact vertical line breaks within blocks. Use empty paragraphs <p></p> or multiple <br> for large vertical gaps to match the exact vertical distances in the original image.
7. **Signatures & Stamps**: If there is a signature, handwritten text, stamp, or seal, represent it with italicized text in brackets, e.g., <p><i>[Imzo]</i></p> or <p><i>[Muhr]</i></p>.
8. **Clean Output**: Return ONLY valid HTML code. No markdown HTML blocks (like ```html), no conversational text, no explanations. Just the HTML elements."""

        def _run_generation(mf):
            return model.generate_content(
                [mf, prompt],
                safety_settings=_OCR_SAFETY,
                generation_config={"temperature": 0.1},
            )

        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(_ocr_executor, _run_generation, myfile),
                timeout=OCR_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error("OCR timeout path=%s after %.1fs (limit=%ss)", image_path, time.perf_counter() - t0, OCR_TIMEOUT)
            result = None

        # Cleanup uploaded file in background
        def _cleanup(name):
            try:
                genai.delete_file(name)
            except Exception:
                pass

        loop.run_in_executor(_ocr_executor, _cleanup, myfile.name)

        text = _extract_text_from_gemini_response(result)
        if text:
            text = text.replace("```html", "").replace("```", "").strip()
            logger.info("OCR done in %.1fs path=%s", time.perf_counter() - t0, image_path)
            return text

        # Retry once with a stricter prompt for forms/tables (often fixes "cho'zilib ketdi" outputs)
        retry_on = os.getenv("OCR_GEMINI_RETRY", "1").strip().lower() not in {"0", "false", "no", "off"}
        if retry_on:
            strict_prompt = (
                prompt
                + "\n\nEXTRA STRICT:\n"
                + "- Prefer HTML <table> for ANY alignment/columns/forms.\n"
                + "- Do NOT use absolute-positioned divs.\n"
                + "- If there are borders/lines, represent them using table borders (style='border:1px solid #000').\n"
                + "- Preserve exact spacing using empty table rows/cells and <br>.\n"
                + "- The image may contain HANDWRITTEN numbers. Read them carefully and put them into the correct cells.\n"
                + "- If a cell is empty, keep it empty.\n"
            )

            def _run_generation_strict(mf):
                return model.generate_content(
                    [mf, strict_prompt],
                    safety_settings=_OCR_SAFETY,
                    generation_config={"temperature": 0.0},
                )

            try:
                result_s = await asyncio.wait_for(
                    loop.run_in_executor(_ocr_executor, _run_generation_strict, myfile),
                    timeout=OCR_TIMEOUT,
                )
            except asyncio.TimeoutError:
                result_s = None
            text_s = _extract_text_from_gemini_response(result_s)
            if text_s:
                text_s = text_s.replace("```html", "").replace("```", "").strip()
                logger.info("OCR strict retry success in %.1fs path=%s", time.perf_counter() - t0, image_path)
                return text_s

        # Birinchi muvaffaqiyatli upload asl fayl bo'lsa, lekin matn bo'sh — RGB PNG qayta urinish
        if not text and not upload_from_norm_only:
            if not norm_png:
                norm_png = await loop.run_in_executor(_ocr_executor, _normalize_image_to_png_sync, image_path)
        if not text and not upload_from_norm_only and norm_png:
            mf2 = await loop.run_in_executor(_ocr_executor, _blocking_upload_path, norm_png)
            if mf2 and mf2.state.name != "FAILED":
                try:
                    result2 = await asyncio.wait_for(
                        loop.run_in_executor(_ocr_executor, _run_generation, mf2),
                        timeout=OCR_TIMEOUT,
                    )
                except asyncio.TimeoutError:
                    result2 = None
                loop.run_in_executor(_ocr_executor, _cleanup, mf2.name)
                text2 = _extract_text_from_gemini_response(result2)
                if text2:
                    text2 = text2.replace("```html", "").replace("```", "").strip()
                    logger.info("OCR (2nd PNG try) done in %.1fs path=%s", time.perf_counter() - t0, image_path)
                    return text2

    except Exception as e:
        logger.error("OCR failed path=%s after %.1fs: %s", image_path, time.perf_counter() - t0, e, exc_info=True)
    finally:
        if norm_png and os.path.isfile(norm_png):
            try:
                os.remove(norm_png)
            except Exception:
                pass
        try:
            if "enh_png" in locals() and enh_png and os.path.isfile(enh_png):
                os.remove(enh_png)
        except Exception:
            pass

    return ""
