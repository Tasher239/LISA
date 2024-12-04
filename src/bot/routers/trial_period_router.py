from aiogram.types import CallbackQuery
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from logger.logging_config import setup_logger

from bot.fsm.states import GetKey, ManageKeys
from bot.initialization.db_processor_init import db_processor
from bot.initialization.outline_processor_init import outline_processor
from bot.utils.send_message import send_key_to_user
from bot.keyboards.keyboards import get_back_button

from database.db_processor import DbProcessor

from datetime import datetime, timedelta

router = Router()
logger = setup_logger()


@router.callback_query(StateFilter(GetKey.buy_key), F.data == "trial_period")
@router.callback_query(StateFilter(ManageKeys.no_active_keys), F.data == "trial_period")
async def handle_trial_key_choice(callback: CallbackQuery, state: FSMContext):
    # Если пользователь выбрал использовать пробный ключ
    # Проверяем, что пользователь не использовал пробный период ранее
    # Если использовал возвращаем сообщение, что пробный период уже заюзан
    # И делаем 2 кнопки - назад и купить ключ

    user_id = callback.from_user.id
    user_id_str = str(user_id)
    session = db_processor.get_session()

    user = (
        session.query(DbProcessor.User).filter_by(user_telegram_id=user_id_str).first()
    )

    if not user:
        user = DbProcessor.User(
            user_telegram_id=user_id_str,
            subscription_status="active",  # тут поменять + добавить инфу о конце периода для ключа
            use_trial_period=False,
        )
        session.add(user)
        session.commit()

    if not user.use_trial_period:
        # обновляем статус использования пробного периода
        # генерируем и высылаем ключ
        user.use_trial_period = True
        session.commit()
        key = outline_processor.create_vpn_key()
        start_date = datetime.now()
        await state.update_data(key_access_url=key.access_url)
        expiration_date = start_date + timedelta(days=2)
        new_key = DbProcessor.Key(
            key_id=key.key_id,
            user_telegram_id=user_id_str,
            expiration_date=expiration_date,
            start_date=start_date,
        )
        session.add(new_key)
        session.commit()

        text = "Ваш пробный ключ готов к использованию. Срок действия - 2 дня."
        await send_key_to_user(callback.message, key, text)
    else:
        await callback.message.answer(
            "Вы уже использовали пробный период. "
            "Вы можете купить ключ или вернуться в главное меню",
            reply_markup=get_back_button(),
        )
