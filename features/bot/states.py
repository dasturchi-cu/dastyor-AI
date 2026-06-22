"""Bot FSM states."""
from aiogram.fsm.state import State, StatesGroup


class ObyektivkaStates(StatesGroup):
    waiting_voice = State()


class CvStates(StatesGroup):
    waiting_input = State()


class ContactStates(StatesGroup):
    waiting_message = State()
