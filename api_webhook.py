import os
import logging
from fastapi import FastAPI, Request, Response
from telegram import Update
from contextlib import asynccontextmanager
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

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "ok", "message": "DASTYOR AI Bot is running"}

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
