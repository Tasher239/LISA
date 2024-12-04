import os

from dotenv import load_dotenv
from database.db_processor import DbProcessor
from datetime import datetime, timedelta

from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery
from aiogram import Router
from aiogram.fsm.context import FSMContext

from bot.fsm.states import ManageKeys
from bot.keyboards.keyboards import get_buttons_for_trial_period, get_back_button
from bot.initialization.outline_processor_init import outline_processor
from bot.initialization.db_processor_init import db_processor

from logger.logging_config import setup_logger

router = Router()

logger = setup_logger()

load_dotenv()
provider_token = os.getenv("PROVIDER_SBER_TOKEN")


# async def delete_previous_message(user_id: int, state: FSMContext):
#     data = await state.get_data()
#     previous_message_id = data.get("previous_message_id")
#     if previous_message_id:
#         try:
#             await bot.delete_message(chat_id=user_id, message_id=previous_message_id)
#             # После удаления сообщения, очищаем previous_message_id
#             await state.update_data(previous_message_id=None)
#         except Exception as e:
#             logger.error(f"Ошибка при удалении сообщения {previous_message_id}: {e}")


def expiration_date_for_user(user: DbProcessor.User):
    """Возвращает дату окончания ключей для пользователя."""
    expiration_dates = {}
    if not user.keys:
        return None
    expiration_dates = {key: key.expiration_date for key in user.keys}
    return expiration_dates


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


async def create_trial_key(user_id: int):
    """Создает пробный ключ для пользователя."""
    key = outline_processor.create_vpn_key()
    session = db_processor.session
    user_id_str = str(user_id)
    user = (
        session.query(DbProcessor.User).filter_by(user_telegram_id=user_id_str).first()
    )
    if not user:
        user = DbProcessor.User(
            user_telegram_id=user_id_str,
            subscription_status="active",
            use_trial_period=True,
        )
        session.add(user)
        session.commit()
    start_date = datetime.now()
    expiration_date = start_date + timedelta(days=2)
    new_key = DbProcessor.Key(
        key_id=key.key_id,
        user_telegram_id=user_id_str,
        expiration_date=expiration_date,
        start_date=start_date,
    )
    session.add(new_key)
    session.commit()
    session.close()
    return key.access_url
