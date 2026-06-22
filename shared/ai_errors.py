"""AI service errors — quota / rate limits."""
from __future__ import annotations

import asyncio

AI_QUOTA_USER_MSG = (
    "⛔ AI limiti vaqtincha tugadi. 1–2 daqiqa kutib qayta urinib ko'ring."
)


class AiQuotaError(Exception):
    """Gemini API quota or rate limit exceeded."""


def is_quota_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return (
        "429" in msg
        or "quota" in msg
        or "rate limit" in msg
        or "rate-limit" in msg
        or "resource exhausted" in msg
        or "exceeded your current quota" in msg
    )


def is_transient_ai_error(exc: BaseException) -> bool:
    """Retry-worthy errors (timeouts, 5xx) — not quota."""
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return True
    if is_quota_error(exc):
        return False
    msg = str(exc).lower()
    return any(
        token in msg
        for token in (
            "503",
            "500",
            "502",
            "504",
            "timeout",
            "timed out",
            "deadline",
            "unavailable",
            "internal error",
            "connection reset",
            "connection error",
            "temporarily",
            "server error",
        )
    )
