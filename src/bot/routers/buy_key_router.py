import os

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LabeledPrice
from dotenv import load_dotenv

from bot.fsm.states import GetKey, MainMenu, ManageKeys
from bot.keyboards.keyboards import get_extension_periods_keyboard, get_period_keyboard
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
    data = await state.get_data()
    selected_key_id = data.get("selected_key_id", None)
    if not selected_key_id:
        await state.update_data(selected_key_id=callback.data.split("_")[1])
    await callback.message.edit_text(
        "Выберите период продления:",
        reply_markup=get_extension_periods_keyboard(),
    )
