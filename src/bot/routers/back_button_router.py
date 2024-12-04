from aiogram.types import CallbackQuery
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state

from bot.fsm.states import MainMenu
from bot.keyboards.keyboards import get_main_menu_keyboard

from logger.logging_config import setup_logger

from bot.routers.main_menu_router import show_main_menu

router = Router()
logger = setup_logger()


@router.callback_query(F.data == "back_to_main_menu")
async def back_button(callback: CallbackQuery, state: FSMContext):
    await state.set_state(default_state)
    # await delete_previous_message(callback.message.chat.id, state)
    await callback.message.answer(
        "Вы вернулись в главное меню. Выберите, что вы хотите сделать",
        reply_markup=get_main_menu_keyboard(),
    )
    await state.set_state(MainMenu.waiting_for_action)
    await callback.answer()
