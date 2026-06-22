"""AI service errors — quota / rate limits."""
from __future__ import annotations

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
