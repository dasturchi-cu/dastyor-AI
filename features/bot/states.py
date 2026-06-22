"""Bot FSM states."""
from aiogram.fsm.state import State, StatesGroup


class ObyektivkaStates(StatesGroup):
    waiting_voice = State()
