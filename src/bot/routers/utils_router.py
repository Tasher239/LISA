from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, LabeledPrice

from bot.fsm.states import MainMenu, GetKey
from bot.initialization.bot_init import bot
from bot.keyboards.keyboards import (
    get_about_us_keyboard,
    get_back_button,
    get_main_menu_keyboard,
)
from bot.lexicon.lexicon import INFO
from bot.utils.string_makers import get_instruction_string
from logger.logging_config import setup_logger

router = Router()
logger = setup_logger()


# фильтр запроса инструкции
@router.callback_query(F.data == "installation_instructions")
async def send_installation_instructions(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    key_access_url = data.get("key_access_url", "URL не найден")
    instructions = get_instruction_string(key_access_url)
    await callback.message.edit_text(
        instructions,
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=get_back_button(),
    )

    await callback.answer()
    await state.set_state(default_state)


# фильтр кнопки в главное меню из любого места
@router.callback_query(F.data == "back_to_main_menu")
async def back_button(callback: CallbackQuery, state: FSMContext):
    cur_state = await state.get_state()
    if cur_state in {GetKey.waiting_for_payment, GetKey.waiting_for_extension_payment}:
        await callback.message.delete()
        data = await state.get_data()
        payment_message_id = data.get("payment_message_id")
        await bot.edit_message_text(
            text="Вы вернулись в главное меню. Выберите, что вы хотите сделать",
            chat_id=callback.message.chat.id,
            message_id=payment_message_id,
            reply_markup=get_main_menu_keyboard(),
        )
        await state.set_state(MainMenu.waiting_for_action)
        await callback.answer()
    else:
        await callback.message.edit_text(
            "Вы вернулись в главное меню. Выберите, что вы хотите сделать",
            reply_markup=get_main_menu_keyboard(),
        )
        await state.set_state(MainMenu.waiting_for_action)
        await callback.answer()


@router.callback_query(StateFilter(MainMenu.about_us), F.data != "back_to_main_menu")
async def show_about_us(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        INFO.ABOUT_US, reply_markup=get_about_us_keyboard(), parse_mode="Markdown"
    )
