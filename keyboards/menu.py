from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class MenuCallback(CallbackData, prefix="menu"):
    action: str


def start_menu_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📄 CV ochish", callback_data=MenuCallback(action="cv").pack())
    kb.button(text="📝 Obyektivka ochish", callback_data=MenuCallback(action="obyektivka").pack())
    kb.adjust(1)
    return kb.as_markup()
