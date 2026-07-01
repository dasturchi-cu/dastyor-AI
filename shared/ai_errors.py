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


def is_network_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(
        token in msg
        for token in (
            "connection refused",
            "connection reset",
            "connection error",
            "network",
            "name or service not known",
            "nodename nor servname",
            "getaddrinfo",
            "ssl",
            "eof occurred",
            "broken pipe",
            "httpx",
            "connect timeout",
        )
    )


def is_failover_error(exc: BaseException) -> bool:
    """Errors that should trigger automatic provider/model/key failover."""
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError, AiQuotaError)):
        return True
    if is_quota_error(exc) or is_transient_ai_error(exc) or is_network_error(exc):
        return True
    msg = str(exc).lower()
    return any(token in msg for token in ("401", "403", "invalid api key", "authentication"))


def translate_error_to_user_message(exc: BaseException) -> str:
    if is_quota_error(exc):
        return "⛔ AI so'rovlar limiti oshib ketdi. 1-2 daqiqa kutib, iltimos qayta urinib ko'ring."
    if is_network_error(exc):
        return "🌐 Internet/Tarmoq ulanishida xatolik yuz berdi. Telegram yoki server aloqasi vaqtincha uzildi. Qayta yuborib ko'ring."
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return "⏳ AI javob berish vaqti tugadi (Timeout). Tarmoq sust yoki so'rov juda katta. Qayta yuborib ko'ring."
    return (
        "❌ AI tahlil qilish jarayonida kutilmagan xatolik yuz berdi.\n\n"
        "💡 <b>Tavsiya:</b> Matnni qisqartirib yoki aniqroq (yozma andozadagidek) yuboring, yoxud 1 daqiqadan so'ng qayta urinib ko'ring."
    )
