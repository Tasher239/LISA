from aiogram.types import CallbackQuery
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from src.logger.logging_config import setup_logger

from bot.fsm.states import ManageKeys
from bot.initialization.db_processor_init import db_processor
from bot.keyboards.keyboards import get_buttons_for_trial_period, get_back_button

from database.user_db import DbProcessor

router = Router()

logger = setup_logger()


@router.callback_query(StateFilter(ManageKeys.choosing_key))
async def choosing_key_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Вы в менеджере ключей")

    # await delete_previous_message(callback.message.chat.id, state)

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
            await state.set_state(ManageKeys.choose_trial_key)

        else:
            # Создание клавиатуры с доступными ключами
            key_details = "Ваши активные ключи:\n"
            for key in user.keys:
                expiration_date = (
                    key.expiration_date.strftime("%Y-%m-%d %H:%M:%S")
                    if key.expiration_date
                    else "Не установлено"
                )
                key_details += (
                    f"- Ключ ID: {key.key_id}, действует до {expiration_date}\n"
                )

            await callback.message.answer(key_details, reply_markup=get_back_button())

    except Exception as e:
        logger.error(f"Ошибка при выборе ключа: {e}")
        await callback.message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")
        await state.clear()
    finally:
        session.close()
    await callback.answer()
