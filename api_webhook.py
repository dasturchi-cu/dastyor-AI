import os
import logging
from fastapi import FastAPI, Request, Response
from telegram import Update
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from main import setup_application

# Setup Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Application
application = setup_application()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize application
    await application.initialize()
    await application.start()
    
    # Set Webhook automatically on startup
    webhook_url = "https://dastyor-ai.onrender.com/webhook"
    logger.info(f"Setting webhook to: {webhook_url}")
    await application.bot.set_webhook(url=webhook_url, drop_pending_updates=True)
    
    logger.info("🚀 Webhook Application Started")
    yield
    # Shutdown
    await application.stop()
    await application.shutdown()
    logger.info("🛑 Webhook Application Stopped")

from fastapi.responses import RedirectResponse

app = FastAPI(lifespan=lifespan)

# Serve Web App Files
app.mount("/webapp", StaticFiles(directory="webapp"), name="webapp")

@app.get("/")
async def root():
    return RedirectResponse(url="/webapp/index.html")

from pydantic import BaseModel
class TranslateRequest(BaseModel):
    text: str
    direction: str

@app.post("/api/translate")
async def api_translate(req: TranslateRequest):
    try:
        from bot.services.ai_service import translate_text
        res = await translate_text(req.text, req.direction)
        return {"translated_text": res}
    except Exception as e:
        logger.error(f"Translate API error: {e}")
        return {"error": str(e)}

from fastapi import File, UploadFile, Form
from typing import List
from telegram import InputFile

@app.post("/api/upload_ocr")
async def api_upload_ocr(telegram_id: str = Form(...), files: List[UploadFile] = File(...)):
    try:
        from bot.handlers.smart_logic import process_ocr_logic
        chat_id = int(telegram_id)
        os.makedirs("temp", exist_ok=True)
        img_paths = []
        for file in files:
            path = f"temp/{file.filename}"
            with open(path, "wb") as f:
                f.write(await file.read())
            img_paths.append(path)
            
        # Process asynchronously so we don't block the request response for too long
        # Send a waiting message via bot
        msg = await application.bot.send_message(chat_id=chat_id, text="⏳ Rasm WebApp orqali qabul qilindi. Word ga o'girilmoqda...")
        
        async def run_ocr_task():
            try:
                await process_ocr_logic(None, None, user_id=chat_id, raw_files=img_paths, bot=application.bot, msg_id=msg.message_id)
            except Exception as ex:
                logger.error(f"OCR background error: {ex}")
        
        import asyncio
        asyncio.create_task(run_ocr_task())
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Upload OCR API error: {e}")
        return {"error": str(e)}

@app.post("/api/upload_pdf")
async def api_upload_pdf(telegram_id: str = Form(...), files: List[UploadFile] = File(...)):
    try:
        chat_id = int(telegram_id)
        os.makedirs("temp", exist_ok=True)
        img_paths = []
        for file in files:
            path = f"temp/{file.filename}"
            with open(path, "wb") as f:
                f.write(await file.read())
            img_paths.append(path)
            
        msg = await application.bot.send_message(chat_id=chat_id, text="⏳ Rasmlar qabul qilindi. PDF tayyorlanmoqda...")
        
        async def run_pdf_task():
            try:
                import img2pdf
                from PyPDF2 import PdfMerger
                pdf_path = f"temp/merged_{chat_id}.pdf"
                with open(pdf_path, "wb") as f:
                    f.write(img2pdf.convert(img_paths))
                
                with open(pdf_path, 'rb') as f:
                    await application.bot.send_document(
                        chat_id=chat_id,
                        document=InputFile(f, filename="DastyorAI_Images.pdf"),
                        caption="✅ **PDF tayyor!**",
                        parse_mode="Markdown"
                    )
                await application.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
                # Cleanup
                for p in img_paths: os.remove(p)
                os.remove(pdf_path)
            except Exception as ex:
                logger.error(f"PDF background error: {ex}")
        
        import asyncio
        asyncio.create_task(run_pdf_task())
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Upload PDF API error: {e}")
        return {"error": str(e)}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/webhook")
async def webhook(request: Request):
    """
    Handle incoming Telegram updates via POST request.
    """
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return Response(status_code=500)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
