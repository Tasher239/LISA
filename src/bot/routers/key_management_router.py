from aiogram.types import CallbackQuery
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from bot.fsm.states import ManageKeys
from bot.initialization.db_processor_init import db_processor
from bot.keyboards.keyboards import (
    get_buttons_for_trial_period,
    get_key_name_choosing_keyboard,
)

from logger.logging_config import setup_logger
from database.db_processor import DbProcessor

router = Router()
logger = setup_logger()


@router.callback_query(F.data == "key_management_pressed")
@router.callback_query(StateFilter(ManageKeys.key_management_pressed))
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
            await callback.message.answer(
                "У вас нет активных ключей, но вы можете испытать пробный период.",
                reply_markup=get_buttons_for_trial_period(),
            )
            await state.set_state(ManageKeys.no_active_keys)

        else:
            # user.keys - это список объектов алхимии.Key
            await callback.message.answer(
                "Выберите ключ для управления:",
                reply_markup=get_key_name_choosing_keyboard(user.keys),
            )
            await state.set_state(ManageKeys.get_key_params)
    except Exception as e:
        logger.error(f"Ошибка при выборе ключа: {e}")
        await callback.message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")
        await state.clear()
    finally:
        session.close()
