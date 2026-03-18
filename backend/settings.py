from __future__ import annotations

import os
from dataclasses import dataclass


def _env(key: str, default: str | None = None) -> str | None:
    val = os.getenv(key)
    if val is None:
        return default
    val = val.strip()
    return val if val else default


@dataclass(frozen=True, slots=True)
class Settings:
    env: str = _env("ENV", "prod") or "prod"

    # Redis
    redis_url: str = _env("REDIS_URL", "redis://redis:6379/0") or "redis://redis:6379/0"

    # Celery (defaults to Redis)
    celery_broker_url: str = _env("CELERY_BROKER_URL", None) or redis_url
    celery_result_backend: str = _env("CELERY_RESULT_BACKEND", None) or redis_url

    # Upload limits
    max_upload_bytes: int = int(_env("MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)) or str(15 * 1024 * 1024))

    # Job storage
    job_ttl_seconds: int = int(_env("JOB_TTL_SECONDS", "3600") or "3600")


_SETTINGS: Settings | None = None


def get_settings() -> Settings:
    global _SETTINGS
    if _SETTINGS is None:
        _SETTINGS = Settings()
    return _SETTINGS

