from aiogram.types import CallbackQuery
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from bot.keyboards.keyboards import get_about_us_keyboard
from bot.fsm.states import MainMenu
from bot.lexicon.lexicon import Texts

from logger.logging_config import setup_logger

router = Router()
logger = setup_logger()


@router.callback_query(StateFilter(MainMenu.about_us), F.data != "back_to_main_menu")
async def show_about_us(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(Texts.ABOUT_US, reply_markup=get_about_us_keyboard())
