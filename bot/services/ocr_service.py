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

        # Use Gemini 2.5 Flash
        model = genai.GenerativeModel('gemini-2.5-flash')

        prompt = """
        You are an expert OCR AI and Document Digitizer.
        Convert the provided image into a structured HTML document that EXACTLY matches the original layout, formatting, and text.
        
        CRITICAL RULES:
        1. **Typography**: Preserve exact font structures. Use <b> or <strong> for bold, <i> or <em> for italics, and <u> for underlines.
        2. **Layout & Alignment**: Preserve text alignment using <div align="center">, <p align="right">, or <h1 align="center">.
        3. **Tables**: If text is side-by-side (like columns) or in a grid/form, YOU MUST USE HTML <table>.
           - Accurately estimate column widths and set them on the first row: <td width="30%">.
           - Map empty cells correctly.
        4. **Structure**: 
           - Use <h1>, <h2>, <h3> for titles/headings.
           - Use <ul>, <ol>, and <li> for lists.
           - Use <p> for paragraphs.
        5. **Spacing**: Use <br> to preserve exact vertical empty lines between paragraphs or items.
        6. **Clean Output**: Return ONLY valid HTML. No markdown formatting (like ```html), no explanations.
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
