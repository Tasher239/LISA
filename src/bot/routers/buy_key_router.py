import uuid
import os

from dotenv import load_dotenv

from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, LabeledPrice
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state

from bot.fsm.states import GetKey
from bot.utils.dicts import prices_dict
from bot.initialization.bot_init import bot
from bot.fsm.states import MainMenu, ManageKeys
from bot.utils.string_makers import get_instruction_string
from bot.keyboards.keyboards import get_back_button, get_period_keyboard

from logger.logging_config import setup_logger

load_dotenv()
provider_token = os.getenv("PROVIDER_SBER_TOKEN")

router = Router()

logger = setup_logger()


@router.callback_query(StateFilter(ManageKeys.no_active_keys),
                       ~F.data.in_(["trial_period", "back_to_main_menu", "installation_instructions"]))
@router.callback_query(StateFilter(MainMenu.waiting_for_action),
                       ~F.data.in_(["trial_period", "back_to_main_menu", "installation_instructions"]))
async def buy_key_menu(callback: CallbackQuery, state: FSMContext):
    await state.set_state(GetKey.buy_key)
    await callback.message.answer(
        "Выберите тип ключа:",
        reply_markup=get_period_keyboard(),
    )
    await callback.answer()


@router.callback_query(
    StateFilter(GetKey.buy_key), ~F.data.in_(["trial_period", "back_to_main_menu"])
)
async def handle_period_selection(callback: CallbackQuery, state: FSMContext):
    # await delete_previous_message(callback.message.chat.id, state)
    selected_period = callback.data.replace("_", " ").title()
    # await callback.message.answer(selected_period.split()[0])

    amount = prices_dict[selected_period.split()[0]]
    prices = [LabeledPrice(label="Ключ от VPN", amount=amount)]
    description = f"Ключ от VPN Outline на {selected_period}"

    # Сохранение выбранного периода в состоянии
    await state.update_data(selected_period=selected_period)
    await state.set_state(GetKey.waiting_for_payment)

    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="Покупка ключа",
        description=description,
        payload=str(uuid.uuid4()),
        provider_token=provider_token,
        start_parameter=str(uuid.uuid4()),
        currency="rub",
        prices=prices,
    )
    await callback.answer()
