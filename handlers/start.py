from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.menu import MenuCallback, start_menu_keyboard
from states.form import FormState

router = Router()

START_TEXT = "Kerakli bo‘limni tanlang:"


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(START_TEXT, reply_markup=start_menu_keyboard())


@router.callback_query(MenuCallback.filter(F.action == "cv"))
async def open_cv_form(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FormState.cv)
    await callback.answer("CV form process boshlandi.")


@router.callback_query(MenuCallback.filter(F.action == "obyektivka"))
async def open_obyektivka_form(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FormState.obyektivka)
    await callback.answer("Obyektivka form process boshlandi.")
