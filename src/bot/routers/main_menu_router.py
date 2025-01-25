from aiogram import F, Router
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.fsm.states import MainMenu, ManageKeys
from bot.keyboards.keyboards import get_main_menu_keyboard
from bot.routers.choice_vpn_type_router import choice_vpn_type
from bot.routers.key_management_router import choosing_key_handler
from bot.routers.utils_router import show_about_us
from bot.utils.send_message import send_message_and_save
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