import json
import uuid
import os

from dotenv import load_dotenv
from database.user_db import DbProcessor
from datetime import datetime, timedelta

from aiogram.filters import CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery

from aiogram import F, Router
from aiogram.fsm.context import FSMContext

from bot.keyboards.keyboards import (
    get_main_menu_keyboard,
    get_period_keyboard,
    get_installation_button,
    get_buttons_for_trial_period,
    get_back_button,
)

from bot.utils.send_message import send_key_to_user
from aiogram.fsm.state import default_state, State, StatesGroup
from bot.fsm.states import MainMenu, GetKey, ManageKeys

from bot.utils.string_makers import get_instruction_string, get_your_key_string

from bot.keyboards.keyboards import get_back_button
from logger.logging_config import setup_logger

from bot.utils.dicts import prices_dict
from bot.initialization.bot_init import bot
from bot.initialization.outline_client_init import outline_processor
from bot.initialization.db_processor_init import db_processor

from bot.utils.send_message import send_message_and_save

router = Router()

logger = setup_logger()

# load_dotenv()
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


@router.callback_query(F.data == "go_back")
async def back_to_main_menu_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(default_state)
    # await delete_previous_message(callback.message.chat.id, state)
    await send_message_and_save(
        callback.message,
        text="Вы вернулись в главное меню. Выберите, что вы хотите сделать",
        state=state,
        reply_markup=get_main_menu_keyboard(),
    )
    await state.set_state(MainMenu.waiting_for_action)
    await callback.answer()


@router.callback_query(StateFilter(GetKey.choosing_period), F.data != "trial_period")
async def handle_period_selection(callback: CallbackQuery, state: FSMContext):
    # await delete_previous_message(callback.message.chat.id, state)
    selected_period = callback.data.replace("_", " ").title()
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


def expiration_date_for_user(user: DbProcessor.User):
    """Возвращает дату окончания ключей для пользователя."""
    expiration_dates = {}
    if not user.keys:
        return None
    expiration_dates = {key: key.expiration_date for key in user.keys}
    return expiration_dates


@router.callback_query(F.data == "installation_instructions")
async def send_installation_instructions(callback: CallbackQuery, state: FSMContext):
    # Пример инструкции
    data = await state.get_data()
    key_access_url = data.get("key_access_url", "URL не найден")
    instructions = get_instruction_string(key_access_url)
    await callback.message.answer(
        instructions,
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=get_back_button(),
    )

    await callback.answer()
    await state.set_state(default_state)


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

            await callback.message.answer(key_details, reply_markup=back_button())

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


@router.callback_query(lambda callback: callback.data == "trial_period")
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
