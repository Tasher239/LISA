import os

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LabeledPrice
from dotenv import load_dotenv

from bot.fsm.states import GetKey, MainMenu, ManageKeys
from bot.keyboards.keyboards import get_extension_periods_keyboard, get_period_keyboard
from bot.initialization.bot_init import bot

from logger.logging_config import setup_logger

router = Router()
logger = setup_logger()


@router.callback_query(F.data.in_(["VPNtype_Outline", "VPNtype_VLESS"]))
async def buy_key_menu(callback: CallbackQuery, state: FSMContext):
    await state.set_state(GetKey.buy_key)
    await state.update_data(vpn_type=callback.data.split("_")[1])
    await callback.message.edit_text(
        "Выберите период подписки:",
        reply_markup=get_period_keyboard(),
    )


@router.callback_query(
    StateFilter(GetKey.waiting_for_payment, GetKey.waiting_for_extension_payment),
    F.data == "back_to_buy_key",
)
async def back_buy_key_menu(callback: CallbackQuery, state: FSMContext):
    await state.set_state(GetKey.buy_key)
    await callback.message.delete()
    data = await state.get_data()
    payment_message_id = data.get("payment_message_id")

    await bot.edit_message_text(
        text="Выберите тип ключа:",
        chat_id=callback.message.chat.id,
        message_id=payment_message_id,
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
