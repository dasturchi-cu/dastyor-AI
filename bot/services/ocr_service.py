"""
OCR Service Module (Async Optimized)
Handles Image-to-Text conversion using Gemini asynchronously to prevent blocking.
Uses a dedicated thread pool so OCR never blocks other bot features.
"""
import logging
import asyncio
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
    Forces 1:1 HTML layout preservation.
    """
    if not GOOGLE_API_KEY:
        return ""

    try:
        logger.info("Attempting Async OCR with Gemini...")

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

        prompt = """You are an expert OCR AI and Document Digitizer.
Convert the provided image into a structured HTML document that EXACTLY matches the original layout, formatting, and text.

CRITICAL RULES:
1. **Typography**: Use <b>/<strong> for bold, <i>/<em> for italics, <u> for underlines.
2. **Alignment**: Use <div align="center">, <p align="right">, or <h1 align="center">.
3. **Tables**: Use HTML <table> for any side-by-side or grid content. Set widths on first row: <td width="30%">.
4. **Structure**: Use <h1>-<h3> for headings, <ul>/<ol>/<li> for lists, <p> for paragraphs.
5. **Spacing**: Use <br> to preserve vertical spacing.
6. **Clean Output**: Return ONLY valid HTML. No markdown, no explanations."""

        # Async generation WITH timeout
        try:
            result = await asyncio.wait_for(
                model.generate_content_async([myfile, prompt]),
                timeout=OCR_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.error(f"OCR Gemini call timed out after {OCR_TIMEOUT}s")
            return ""

        # Cleanup uploaded file in background
        def _cleanup(name):
            try: genai.delete_file(name)
            except Exception: pass
        loop.run_in_executor(_ocr_executor, _cleanup, myfile.name)

        if result and result.text:
            text = result.text.replace("```html", "").replace("```", "").strip()
            logger.info("Gemini Async OCR success")
            return text

    except Exception as e:
        logger.error(f"Gemini Async OCR failed: {e}", exc_info=True)

    return ""
