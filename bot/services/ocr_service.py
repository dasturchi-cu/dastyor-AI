"""
OCR Service Module (Async Optimized)
Handles Image-to-Text conversion using Gemini asynchronously to prevent blocking.
Uses a dedicated thread pool so OCR never blocks other bot features.
"""
import logging
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
import google.generativeai as genai
from config import GOOGLE_API_KEY

logger = logging.getLogger(__name__)

# Dedicated thread pool for OCR tasks — prevents blocking other bot features
_ocr_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ocr")

# OCR timeout (seconds) — prevents the bot from hanging on slow Gemini responses
OCR_TIMEOUT = 120

async def extract_text_from_image(image_path: str) -> str:
    """
    Extracts text from an image file using Gemini asynchronously.
    Forces 1:1 HTML layout preservation. Does not block the event loop.
    """
    if not GOOGLE_API_KEY:
        return ""

    t0 = time.perf_counter()
    try:
        logger.info("OCR extract started path=%s", image_path)

        loop = asyncio.get_running_loop()

        def blocking_upload():
            """Upload file and wait for Gemini to process it (runs in thread)."""
            try:
                myfile = genai.upload_file(image_path)
                waited = 0
                while myfile.state.name == "PROCESSING" and waited < 30:
                    import time
                    time.sleep(1)
                    waited += 1
                    try:
                        myfile = genai.get_file(myfile.name)
                    except Exception:
                        break
                return myfile
            except Exception as e:
                logger.error(f"OCR upload failed: {e}")
                return None

        myfile = await loop.run_in_executor(_ocr_executor, blocking_upload)

        if not myfile or myfile.state.name == "FAILED":
            logger.error("Gemini file upload/processing failed.")
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

        # Run the heavy multimodal generation in a thread so the event loop is never blocked
        def _run_generation():
            return model.generate_content([myfile, prompt])

        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(_ocr_executor, _run_generation),
                timeout=OCR_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.error("OCR timeout path=%s after %.1fs (limit=%ss)", image_path, time.perf_counter() - t0, OCR_TIMEOUT)
            return ""

        # Cleanup uploaded file in background
        def _cleanup(name):
            try: genai.delete_file(name)
            except Exception: pass
        loop.run_in_executor(_ocr_executor, _cleanup, myfile.name)

        if result and result.text:
            text = result.text.replace("```html", "").replace("```", "").strip()
            logger.info("OCR done in %.1fs path=%s", time.perf_counter() - t0, image_path)
            return text

    except Exception as e:
        logger.error("OCR failed path=%s after %.1fs: %s", image_path, time.perf_counter() - t0, e, exc_info=True)

    return ""
