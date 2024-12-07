from aiogram.types import Message, CallbackQuery
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.state import default_state

from bot.keyboards.keyboards import get_main_menu_keyboard
from bot.fsm.states import MainMenu, ManageKeys
from bot.utils.send_message import send_message_and_save
from bot.routers.key_management_router import choosing_key_handler
from bot.routers.buy_key_router import buy_key_menu
from bot.routers.about_us_router import show_about_us


from logger.logging_config import setup_logger

router = Router()
logger = setup_logger()


@router.message(CommandStart())
async def show_main_menu(
    message_or_callback: Message | CallbackQuery, state: FSMContext
):
    await state.clear()
    target = (
        message_or_callback.message
        if isinstance(message_or_callback, CallbackQuery)
        else message_or_callback
    )
    await send_message_and_save(
        target,
        text="Привет! Добро пожаловать в систему неограниченного "
        "безопасного доступа в Интернет «LISA». Выберите, "
        "что вы хотите сделать",
        state=state,
        reply_markup=get_main_menu_keyboard(),
    )
    await state.set_state(MainMenu.waiting_for_action)


@router.callback_query(StateFilter(MainMenu.waiting_for_action))
async def main_menu_handler(callback: CallbackQuery, state: FSMContext):
    # await delete_previous_message(callback.message.chat.id, state)
    action = callback.data
    if action == "get_keys_pressed":
        await buy_key_menu(callback, state)
    elif action == "key_management_pressed":
        await state.set_state(ManageKeys.choosing_key)
        await choosing_key_handler(
            callback, state
        )  # тут идет связь с роутером менеджера ключей
    elif action == "about_us":
        await state.set_state(MainMenu.about_us)
        await show_about_us(callback, state)
    else:
        await send_message_and_save(
            callback.message, "Неизвестное действие.", state=state
        )
    await callback.answer()
