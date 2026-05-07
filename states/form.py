from aiogram.fsm.state import State, StatesGroup


class FormState(StatesGroup):
    cv = State()
    obyektivka = State()
