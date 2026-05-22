"""Bot ichidagi muhim hodisalar — action_logs (mavjud jadval)."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def log_bot_event(user_id: int, event: str, meta: dict[str, Any] | None = None) -> None:
    if not user_id or not event:
        return
    try:
        from bot.services.supabase_db import db_insert_system_log, has_db

        if has_db():
            db_insert_system_log(
                int(user_id),
                None,
                "BOT",
                str(event)[:160],
                status="ok",
                metadata=meta if isinstance(meta, dict) else None,
            )
            return
    except Exception as e:
        logger.debug("log_bot_event system_logs %s: %s", event, e)
    try:
        from bot.services.supabase_db import db_insert_action_log

        db_insert_action_log(int(user_id), event, None, meta or {})
    except Exception as e:
        logger.debug("log_bot_event %s: %s", event, e)
