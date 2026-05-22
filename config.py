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

# === SUPABASE ===
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# === BUSINESS CONFIG ===
# Daily free usage limit per user (0 = unlimited)
DAILY_FREE_LIMIT = int(os.getenv("DAILY_FREE_LIMIT", "10"))

# WebApp (Telegram Mini App) — bot va backend bir xil domenga ishora qilishi kerak
WEBAPP_VERSION = os.getenv("WEBAPP_VERSION", "20260322")
_DEFAULT_WEBAPP = "https://dastyor-ai.onrender.com/webapp"


def resolve_webapp_base() -> str:
    """
    Telegram WebApp URL — env bo‘sh bo‘lsa SITE_BASE_URL yoki WEBHOOK_URL dan tuziladi.
    Railway da faqat WEBHOOK_URL bo‘lsa ham forma ochiladi.
    """
    explicit = (os.getenv("WEBAPP_BASE") or "").strip().rstrip("/")
    if explicit.startswith("https://"):
        return explicit

    site = (os.getenv("SITE_BASE_URL") or "").strip().rstrip("/")
    if site.startswith("https://"):
        return site if site.endswith("/webapp") else f"{site}/webapp"

    webhook = (os.getenv("WEBHOOK_URL") or "").strip().rstrip("/")
    if webhook.startswith("https://"):
        root = webhook.split("/webhook")[0].split("/api/webhook")[0].rstrip("/")
        if root.endswith("/webapp"):
            return root
        return f"{root}/webapp"

    return _DEFAULT_WEBAPP.rstrip("/")


WEBAPP_BASE = resolve_webapp_base()

if not BOT_TOKEN:
    logger.critical("BOT_TOKEN is missing! Please create a .env file with BOT_TOKEN=your_token_here")

if not GOOGLE_API_KEY:
    logger.warning("GOOGLE_API_KEY is missing. AI features will be limited.")
