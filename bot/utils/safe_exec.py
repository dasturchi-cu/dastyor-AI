import logging
from typing import Awaitable, Callable

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def _capture_exception(e: Exception) -> None:
    try:
        import sentry_sdk  # type: ignore

        sentry_sdk.capture_exception(e)
    except Exception:
        pass


async def safe_execute(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    action: Callable[[], Awaitable[None]],
    *,
    user_error_text: str = "⚠️ Xatolik yuz berdi, qayta urinib ko'ring.",
    log_message: str = "Unhandled router error",
) -> None:
    try:
        await action()
    except Exception as e:
        logger.error("%s: %s", log_message, e, exc_info=True)
        _capture_exception(e)
        try:
            if update and update.message:
                await update.message.reply_text(user_error_text)
        except Exception:
            pass
