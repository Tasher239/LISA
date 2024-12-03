from aiogram.types import Message, CallbackQuery
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.state import default_state

from src.logger.logging_config import setup_logger

from bot.keyboards.keyboards import get_period_keyboard
from bot.keyboards.keyboards import (get_main_menu_keyboard, )
from bot.fsm.states import MainMenu, GetKey, ManageKeys
from bot.utils.send_message import send_message_and_save
from bot.routers.key_management_router import choosing_key_handler

router = Router()

logger = setup_logger()

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
        await send_message_and_save(
            callback.message,
            text="Выберите период действия ключа:",
            state=state,
            reply_markup=get_period_keyboard(),
        )
        await state.set_state(GetKey.choosing_period)
    elif action == "key_management_pressed":
        await state.set_state(ManageKeys.choosing_key)
        await choosing_key_handler(callback, state) # тут идет связь с роутером менеджера ключей
    else:
        await send_message_and_save(
            callback.message, "Неизвестное действие.", state=state
        )
    await callback.answer()

@router.message(CommandStart() or StateFilter(default_state))
async def process_start_command(message: Message, state: FSMContext):
    await show_main_menu(message, state)


@router.callback_query(F.data == "to_main_menu")
async def go_to_main_menu(callback: CallbackQuery, state: FSMContext):
    await show_main_menu(callback, state)
    await callback.answer()
