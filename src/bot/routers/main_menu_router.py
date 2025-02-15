from aiogram import F, Router
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.fsm.states import MainMenu
from bot.keyboards.keyboards import get_main_menu_keyboard

from logger.logging_config import setup_logger

router = Router()
logger = setup_logger()


@router.message(CommandStart())
async def show_main_menu(message: Message, state: FSMContext):
    await state.clear()
    prompt = await message.answer(
        text="Привет! Добро пожаловать в систему неограниченного "
        "безопасного доступа в Интернет «LISA». Выберите, "
        "что вы хотите сделать",
        reply_markup=get_main_menu_keyboard(),
    )
    await state.update_data(prompt_msg_id=prompt.message_id)
    await state.set_state(MainMenu.waiting_for_action)
