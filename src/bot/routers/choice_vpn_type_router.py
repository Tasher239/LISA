import os

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LabeledPrice
from dotenv import load_dotenv

from bot.fsm.states import GetKey
from bot.keyboards.keyboards import get_choice_vpn_type_keyboard
from logger.logging_config import setup_logger

router = Router()
logger = setup_logger()


@router.callback_query(F.data.in_(['choice_vpn_type', 'back_to_choice_vpn_type']))
async def choice_vpn_type(callback: CallbackQuery, state: FSMContext):
    await state.set_state(GetKey.choosing_vpn_protocol_type)
    await callback.message.edit_text(
        "Выберите тип подключения:",
        reply_markup=get_choice_vpn_type_keyboard(),
    )