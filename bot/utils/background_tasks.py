"""
Background task runner for heavy operations.

Use asyncio.create_task() from handlers so the bot event loop is never blocked.
Heavy work (OCR, PDF build, doc generation) should run in background and send
results when done. This keeps the bot responsive for all users.
"""
import asyncio
import logging

logger = logging.getLogger(__name__)


def run_in_background(coro):
    """
    Schedule a coroutine to run in the background. Use from message handlers
    to avoid blocking the event loop. Errors are logged and not re-raised.
    """
    task = asyncio.create_task(coro)
    task.add_done_callback(_done_callback)
    return task


def _done_callback(fut):
    try:
        fut.result()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error("Background task failed: %s", e, exc_info=True)
