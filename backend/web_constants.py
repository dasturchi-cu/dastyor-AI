import os

SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://dastyor-ai.onrender.com")
PREMIUM_ADMIN_GROUP_ID = int(os.getenv("PREMIUM_ADMIN_GROUP_ID", "-1003457224552"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "DastyorAiBot")
try:
    from config import WEBAPP_BASE as WEBAPP_BASE  # noqa: F401 — resolve_webapp_base()
except Exception:
    WEBAPP_BASE = (
        os.getenv("WEBAPP_BASE", "https://dastyor-ai.onrender.com/webapp") or ""
    ).strip().rstrip("/")
WEBAPP_VERSION = os.getenv("WEBAPP_VERSION", "20260322")

# Text limits (aligned with bot + Gemini batching in ai_service)
SPELLCHECK_MAX_CHARS = int(os.getenv("SPELLCHECK_MAX_CHARS", "50000"))
TRANSLIT_MAX_CHARS = 50_000
TRANSLATE_MAX_CHARS = 5000
NOTIFY_MAX_CHARS = 4000
