import uuid
import os

from dotenv import load_dotenv

from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, LabeledPrice
from aiogram import F, Router
from aiogram.fsm.context import FSMContext

from bot.fsm.states import GetKey

from bot.fsm.states import MainMenu, ManageKeys
from bot.keyboards.keyboards import get_period_keyboard, get_extension_periods_keyboard

from logger.logging_config import setup_logger

load_dotenv()
provider_token = os.getenv("PROVIDER_SBER_TOKEN")

router = Router()
logger = setup_logger()


@router.callback_query(F.data == "get_keys_pressed")
@router.callback_query(
    StateFilter(ManageKeys.no_active_keys),
    ~F.data.in_(["trial_period", "back_to_main_menu", "installation_instructions"]),
)
@router.callback_query(
    StateFilter(MainMenu.waiting_for_action),
    ~F.data.in_(["trial_period", "back_to_main_menu", "installation_instructions"]),
)
async def buy_key_menu(callback: CallbackQuery, state: FSMContext):
    await state.set_state(GetKey.buy_key)
    await callback.message.edit_text(
        "Выберите тип ключа:",
        reply_markup=get_period_keyboard(),
    )


@router.callback_query(F.data.startswith("extend_"))
async def extension_period_key_menu(callback: CallbackQuery, state: FSMContext):
    await state.set_state(GetKey.choice_extension_period)
    await callback.message.edit_text(
        "Выберите период продления:",
        reply_markup=get_extension_periods_keyboard(),
    )
