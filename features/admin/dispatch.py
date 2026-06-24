"""Admin menu dispatcher — works from any FSM state."""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config.settings import settings
from features.admin import actions as admin_actions
from shared.keyboards import (
    ADMIN_BTN_ACTIVITY,
    ADMIN_BTN_AI,
    ADMIN_BTN_BROADCAST,
    ADMIN_BTN_CLOSE,
    ADMIN_BTN_DASHBOARD,
    ADMIN_BTN_SECURITY,
    ADMIN_BTN_ERRORS,
    ADMIN_BTN_EXPORT,
    ADMIN_BTN_FILES,
    ADMIN_BTN_PAYMENTS,
    ADMIN_BTN_PENDING,
    ADMIN_BTN_SEARCH,
    ADMIN_BTN_SETTINGS,
    ADMIN_BTN_STATS,
    ADMIN_BTN_TOP,
    ADMIN_BTN_USERS,
    is_admin_menu_button,
)

logger = logging.getLogger(__name__)

MenuHandler = Callable[[Message, FSMContext], Awaitable[None]]

MENU_DISPATCH: dict[str, MenuHandler] = {
    ADMIN_BTN_USERS: admin_actions.handle_users,
    ADMIN_BTN_SEARCH: admin_actions.handle_search_prompt,
    ADMIN_BTN_PAYMENTS: admin_actions.handle_payments_menu,
    ADMIN_BTN_PENDING: admin_actions.handle_pending_payments,
    ADMIN_BTN_STATS: admin_actions.handle_stats,
    ADMIN_BTN_ACTIVITY: admin_actions.handle_activity,
    ADMIN_BTN_BROADCAST: admin_actions.handle_broadcast_prompt,
    ADMIN_BTN_EXPORT: admin_actions.handle_export_menu,
    ADMIN_BTN_TOP: admin_actions.handle_top,
    ADMIN_BTN_ERRORS: admin_actions.handle_errors,
    ADMIN_BTN_FILES: admin_actions.handle_files,
    ADMIN_BTN_SETTINGS: admin_actions.handle_settings,
    ADMIN_BTN_DASHBOARD: admin_actions.handle_dashboard_refresh,
    ADMIN_BTN_SECURITY: admin_actions.handle_security_dashboard,
    ADMIN_BTN_AI: admin_actions.handle_ai_status,
    ADMIN_BTN_CLOSE: admin_actions.handle_close,
}


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_user_ids


async def dispatch_admin_menu(message: Message, state: FSMContext) -> bool:
    """Route admin menu button. Returns True if handled."""
    text = (message.text or "").strip()
    if not is_admin_menu_button(text):
        return False
    if not message.from_user or not is_admin(message.from_user.id):
        return False

    handler = MENU_DISPATCH.get(text)
    if not handler:
        logger.warning("Admin menu tugmasi handler yo'q: %r", text)
        await message.answer(f"❌ Tugma hali ulanmagan: {text}")
        return True

    action = text
    try:
        await state.clear()
        await handler(message, state)
        logger.info("Admin action OK: %s (user=%s)", action, message.from_user.id)
    except Exception as exc:
        logger.exception("Admin action FAILED: %s — %s", action, exc)
        await message.answer(
            f"❌ <b>Xatolik</b>\n\n"
            f"Tugma: {action}\n"
            f"Sabab: {exc}\n\n"
            f"Qayta urinib ko'ring yoki /admin bosing."
        )
    return True


def all_menu_buttons() -> frozenset[str]:
    return frozenset(MENU_DISPATCH.keys())
