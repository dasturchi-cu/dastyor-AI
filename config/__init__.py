"""Application configuration."""
from config.settings import settings, resolve_webapp_base

BOT_TOKEN = settings.bot_token
GOOGLE_API_KEY = settings.google_api_key
ADMIN_USER_ID = ",".join(str(x) for x in settings.admin_user_ids)
WEBAPP_BASE = settings.webapp_base
WEBAPP_VERSION = settings.webapp_version

__all__ = [
    "settings",
    "resolve_webapp_base",
    "BOT_TOKEN",
    "GOOGLE_API_KEY",
    "ADMIN_USER_ID",
    "WEBAPP_BASE",
    "WEBAPP_VERSION",
]
