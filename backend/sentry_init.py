"""
Sentry initialization for both FastAPI and Telegram bot.

Usage:
  from backend.sentry_init import init_sentry
  init_sentry(service_name="backend")  # or "bot"
"""
from __future__ import annotations

import os


def _f(key: str, default: str) -> float:
    try:
        return float(os.getenv(key, default) or default)
    except Exception:
        return float(default)


def init_sentry(*, service_name: str) -> None:
    dsn = (os.getenv("SENTRY_DSN") or "").strip()
    if not dsn:
        return

    env = (os.getenv("SENTRY_ENVIRONMENT") or os.getenv("ENV") or "prod").strip()[:32]
    release = (os.getenv("SENTRY_RELEASE") or os.getenv("WEBAPP_VERSION") or "").strip()[:64] or None

    traces = _f("SENTRY_TRACES_SAMPLE_RATE", "0.15")
    profiles = _f("SENTRY_PROFILES_SAMPLE_RATE", "0.0")

    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.httpx import HttpxIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    logging_integration = LoggingIntegration(
        level=None,        # keep existing log level
        event_level="ERROR",
    )

    sentry_sdk.init(
        dsn=dsn,
        environment=env,
        release=release,
        server_name=service_name,
        send_default_pii=True,
        enable_tracing=(traces > 0.0),
        traces_sample_rate=max(0.0, min(1.0, traces)),
        profiles_sample_rate=max(0.0, min(1.0, profiles)),
        integrations=[
            # Backend + WebApp
            FastApiIntegration(),
            # Outbound calls
            HttpxIntegration(),
            # Background jobs
            CeleryIntegration(),
            # Cache/queue
            RedisIntegration(),
            # Python logging -> Sentry events
            logging_integration,
        ],
    )

