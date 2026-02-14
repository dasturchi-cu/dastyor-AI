import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")

# === BUSINESS CONFIG ===
# Daily free usage limit per user (0 = unlimited)
DAILY_FREE_LIMIT = int(os.getenv("DAILY_FREE_LIMIT", "10"))

if not BOT_TOKEN:
    logger.critical("BOT_TOKEN is missing! Please create a .env file with BOT_TOKEN=your_token_here")

if not GOOGLE_API_KEY:
    logger.warning("GOOGLE_API_KEY is missing. AI features will be limited.")
