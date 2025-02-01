from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.fsm.states import ManageKeys, MainMenu
from bot.initialization.db_processor_init import db_processor
from bot.keyboards.keyboards import (
    get_buttons_for_trial_period,
    get_key_name_choosing_keyboard,
)

from database.db_processor import DbProcessor

from logger.logging_config import setup_logger

router = Router()
logger = setup_logger()


@router.callback_query(
    StateFilter(
        ManageKeys.no_active_keys,
        MainMenu.waiting_for_action,
        ManageKeys.choose_key_action,
    ),
    F.data == "key_management_pressed",
)
# @router.callback_query(StateFilter(MainMenu.waiting_for_action), F.data == "key_management_pressed")
async def choosing_key_handler(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_id_str = str(user_id)
    session = db_processor.get_session()

    try:
        user = (
            session.query(DbProcessor.User)
            .filter_by(user_telegram_id=user_id_str)
            .first()
        )
        if not user or len(user.keys) == 0:
            await state.set_state(ManageKeys.no_active_keys)
            await callback.message.edit_text(
                "У вас нет активных ключей, но вы можете получить пробный период или приобрести ключ",
                reply_markup=get_buttons_for_trial_period(),
            )

        else:
            # ids_key = [key.id for key in user.keys]
            keyboard = await get_key_name_choosing_keyboard(user.keys)

            # user.keys - это список объектов алхимии Key
            await callback.message.edit_text(
                "Выберите ключ для управления:",
                reply_markup=keyboard,
            )
            await state.set_state(ManageKeys.get_key_params)
    except Exception as e:
        logger.error(f"Ошибка при выборе ключа: {e}")
        await callback.message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")
        await state.clear()
    finally:
        session.close()
