"""Central application settings."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
RECEIPTS_DIR = UPLOADS_DIR / "receipts"
GENERATED_DIR = UPLOADS_DIR / "generated"
DB_PATH = DATA_DIR / "hujjatchi.db"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
WEBAPP_DIR = PROJECT_ROOT / "webapp"


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key) or os.getenv(f"\ufeff{key}") or default).strip()


def _env_int(key: str, default: int = 0) -> int:
    raw = _env(key)
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


def _admin_ids() -> set[int]:
    raw = _env("ADMIN_USER_ID")
    return {int(v.strip()) for v in raw.split(",") if v.strip().isdigit()}


def resolve_webapp_base() -> str:
    explicit = _env("WEBAPP_BASE").rstrip("/")
    if explicit.startswith("https://"):
        return explicit

    site = _env("SITE_BASE_URL").rstrip("/")
    if site.startswith("https://"):
        return site if site.endswith("/webapp") else f"{site}/webapp"

    webhook = _env("WEBHOOK_URL").rstrip("/")
    if webhook.startswith("https://"):
        root = webhook.split("/webhook")[0].split("/api/webhook")[0].rstrip("/")
        return root if root.endswith("/webapp") else f"{root}/webapp"

    return "https://localhost/webapp"


@dataclass(frozen=True)
class Settings:
    bot_token: str = field(default_factory=lambda: _env("BOT_TOKEN"))
    bot_username: str = field(default_factory=lambda: _env("BOT_USERNAME", "DastyorAiBot").lstrip("@"))
    google_api_key: str = field(default_factory=lambda: _env("GOOGLE_API_KEY"))
    admin_user_ids: frozenset[int] = field(default_factory=lambda: frozenset(_admin_ids()))
    support_group_id: int = field(default_factory=lambda: _env_int("SUPPORT_GROUP_ID", -1003457224552))
    premium_admin_group_id: int = field(
        default_factory=lambda: _env_int("PREMIUM_ADMIN_GROUP_ID", _env_int("SUPPORT_GROUP_ID", -1003457224552))
    )
    payment_card_number: str = field(default_factory=lambda: _env("PAYMENT_CARD_NUMBER", "9860 1201 7225 8424"))
    payment_card_owner: str = field(default_factory=lambda: _env("PAYMENT_CARD_OWNER", "DILNOZA MOMINOVA"))
    single_doc_price_uzs: int = field(default_factory=lambda: _env_int("SINGLE_DOC_PRICE_UZS", 5000))
    webapp_base: str = field(default_factory=resolve_webapp_base)
    webapp_version: str = field(default_factory=lambda: _env("WEBAPP_VERSION", "20260622"))
    site_base_url: str = field(default_factory=lambda: _env("SITE_BASE_URL").rstrip("/"))
    webhook_url: str = field(default_factory=lambda: _env("WEBHOOK_URL"))
    port: int = field(default_factory=lambda: _env_int("PORT", 8000))
    db_path: Path = field(default_factory=lambda: DB_PATH)
    rate_limit_per_minute: int = field(default_factory=lambda: _env_int("RATE_LIMIT_PER_MINUTE", 60))


settings = Settings()

if not settings.bot_token:
    logger.critical("BOT_TOKEN is missing — create .env with BOT_TOKEN=...")
if not settings.google_api_key:
    logger.warning("GOOGLE_API_KEY missing — AI voice features disabled")
