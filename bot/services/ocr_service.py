"""
OCR Service Module (Async Optimized)
Handles Image-to-Text conversion using Gemini asynchronously to prevent blocking.
"""
import logging
import asyncio
import google.generativeai as genai
from config import GOOGLE_API_KEY

logger = logging.getLogger(__name__)

async def extract_text_from_image(image_path: str) -> str:
    """
    Extracts text from an image file using Gemini 3 Flash asynchronously.
    Forces 1:1 HTML layout preservation.
    """
    if not GOOGLE_API_KEY:
        return ""
        
    try:
        logger.info("Attempting Async OCR with Gemini 3 Flash (1:1 Layout)...")
        genai.configure(api_key=GOOGLE_API_KEY)
        
        # Run blocking upload/configure actions in thread
        loop = asyncio.get_running_loop()
        
        def blocking_upload():
            """Handle file upload synchronously in a thread"""
            try:
                myfile = genai.upload_file(image_path)
                # Wait for processing
                waited = 0
                while myfile.state.name == "PROCESSING" and waited < 10:
                    import time
                    time.sleep(1)
                    waited += 1
                    try:
                        myfile = genai.get_file(myfile.name)
                    except:
                        break
                return myfile
            except Exception as e:
                logger.error(f"Upload failed: {e}")
                return None

        # Execute upload in thread
        myfile = await loop.run_in_executor(None, blocking_upload)
        
        if not myfile:
            return ""
            
        if myfile.state.name == "FAILED":
            logger.error("Gemini file processing failed state.")
            return ""

        # Use Gemini 3 Flash
        model = genai.GenerativeModel('gemini-3-flash-preview')

        prompt = """
        You are a professional Document Digitizer.
        Your goal is to convert this image into an HTML document that represents the ORIGINAL LAYOUT EXACTLY 1:1.
        
        CRITICAL RULES:
        1. **Tables & Widgets**: If the document looks like a form or has columns, YOU MUST USE HTML `<table>`.
        2. **Column Widths**: You MUST estimate the width of each column and add `width="X%"` to the `<td>` or `<th>` tags. Example: `<td width="30%">`.
        3. **Margins & Spacing**: Use `<br>` for empty lines to preserve vertical spacing.
        4. **Structuring**:
           - If text is side-by-side, use a table row with 2 cells.
           - Preserve alignment (`align="center"`, `align="right"`).
        5. **Formatting**: Bold (`<b>`), Italic (`<i>`), Headers (`<h1>`).
        6. **Output**: Return ONLY the HTML code. No markdown text.
        """
        
        # Async generation
        result = await model.generate_content_async([myfile, prompt])
        
        # Cleanup file in background
        async def cleanup():
            try:
                genai.delete_file(myfile.name)
            except: pass
        asyncio.create_task(cleanup())
        
        if result and result.text:
            text = result.text.replace("```html", "").replace("```", "").strip()
            logger.info("Gemini Async OCR success")
            return text
            
    except Exception as e:
        logger.error(f"Gemini Async OCR failed: {e}", exc_info=True)
            
    return ""
