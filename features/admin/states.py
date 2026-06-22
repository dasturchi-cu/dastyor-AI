"""Admin panel FSM states."""
from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    broadcast_text = State()
    user_search = State()
    credit_amount = State()
    dm_user_text = State()
    support_reply = State()
