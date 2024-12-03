from aiogram.types import Message, CallbackQuery
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state

from logger.logging_config import setup_logger

from bot.keyboards.keyboards import get_prodlenie_keyboard
from bot.keyboards.keyboards import (get_main_menu_keyboard, )
from bot.fsm.states import MainMenu, GetKey, ManageKeys, Subscription_prodl
from bot.utils.dicts import prices_dict_prodl
from bot.routers.key_management_router import choosing_key_handler

router = Router()
router.message.filter(F.data == "extend_now")
logger = setup_logger()

@router.message()
async def prodlenie(message: Message, state: FSMContext):
    if (F.data == "extend_now"):
        await message.answer(
            text="Выберите период продления:",
            reply_markup=get_prodlenie_keyboard(),
            state=GetKey.prodlenie
        )


