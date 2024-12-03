import json
import uuid

import os
from database.user_db import DbProcessor
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from outline_vpn.outline_vpn import OutlineVPN

from bot.keyboards.keyboards import (
    get_main_menu_keyboard,
    get_period_keyboard,
    get_installation_button,
    get_buttons_for_trial_period,
    back_button,
    get_instruction_keyboard,
)

from aiogram.fsm.state import default_state, State, StatesGroup
from bot.fsm.states import MainMenu, GetKey, ManageKeys

from bot.utils.string_makers import get_instruction_string, get_your_key_string
from dotenv import load_dotenv

from bot.logger.logging_config import setup_logger

from bot.utils.dicts import prices_dict
from bot.utils.outline_processor import OutlineProcessor

router = Router()
db_processor = DbProcessor()
session = db_processor.Session()

load_dotenv()

BOT_TOKEN = os.getenv("TOKEN")
api_url = os.getenv("API_URL")
cert_sha256 = os.getenv("CERT_SHA")
provider_token = os.getenv("PROVIDER_SBER_TOKEN")

bot = Bot(token=BOT_TOKEN)

client = OutlineVPN(api_url=api_url, cert_sha256=cert_sha256)
outline_processor = OutlineProcessor(client)

logger = setup_logger()


async def delete_previous_message(user_id: int, state: FSMContext):
    data = await state.get_data()
    previous_message_id = data.get("previous_message_id")
    if previous_message_id:
        try:
            await bot.delete_message(chat_id=user_id, message_id=previous_message_id)
            # После удаления сообщения, очищаем previous_message_id
            await state.update_data(previous_message_id=None)
        except Exception as e:
            logger.error(f"Ошибка при удалении сообщения {previous_message_id}: {e}")


async def send_message_and_save(message, text, state: FSMContext, **kwargs):
    sent_message = await message.answer(text, **kwargs)
    await state.update_data(previous_message_id=sent_message.message_id)
    return sent_message


async def show_main_menu(
    message_or_callback: Message | CallbackQuery, state: FSMContext
):
    await state.clear()
    target = (
        message_or_callback.message
        if isinstance(message_or_callback, CallbackQuery)
        else message_or_callback
    )
    await send_message_and_save(
        target,
        text="Привет! Добро пожаловать в систему неограниченного "
        "безопасного доступа в Интернет «LISA». Выберите, "
        "что вы хотите сделать",
        state=state,
        reply_markup=get_main_menu_keyboard(),
    )
    await state.set_state(MainMenu.waiting_for_action)


@router.message(CommandStart() or StateFilter(default_state))
async def process_start_command(message: Message, state: FSMContext):
    await show_main_menu(message, state)


@router.callback_query(F.data == "to_main_menu")
async def go_to_main_menu(callback: CallbackQuery, state: FSMContext):
    await show_main_menu(callback, state)
    await callback.answer()


@router.callback_query(StateFilter(MainMenu.waiting_for_action))
async def main_menu_handler(callback: CallbackQuery, state: FSMContext):
    # await delete_previous_message(callback.message.chat.id, state)
    action = callback.data
    if action == "get_keys_pressed":
        await send_message_and_save(
            callback.message,
            text="Выберите период действия ключа:",
            state=state,
            reply_markup=get_period_keyboard(),
        )
        await state.set_state(GetKey.choosing_period)
    elif action == "key_management_pressed":
        await state.set_state(ManageKeys.choosing_key)
        await choosing_key_handler(callback, state)
    else:
        await send_message_and_save(
            callback.message, "Неизвестное действие.", state=state
        )
    await callback.answer()


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


"""
Метод answer_pre_checkout_query() отвечает на запрос Telegram о предварительной проверке платежа.
В pre_checkout_q.id передается уникальный идентификатор запроса, полученный из объекта PreCheckoutQuery.
Параметр ok=True указывает, что запрос на предварительную проверку платежа был принят и все в порядке (платеж можно продолжать).
Если вы хотите отклонить платеж, вы можете установить ok=False и добавить описание причины отклонения через параметр error_message.
"""


@router.pre_checkout_query()
async def pre_checkout_query(pre_checkout_q: PreCheckoutQuery):
    # Проверяем данные платежа
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)


# Обработчик успешного платежа
@router.message(
    StateFilter(GetKey.waiting_for_payment), lambda message: message.successful_payment
)
async def successful_payment(message: Message, state: FSMContext):
    try:
        # Логирование успешного платежа
        log_payment_details(message)
        # Создание нового ключа VPN
        key = create_vpn_key()
        await send_key_to_user(message, key)
        # Обновление базы данных
        data = await state.get_data()
        period = data.get("selected_period", "1 Month")
        await update_database_with_key(message.from_user.id, key, period)
        # Отправка инструкций по установке
        await state.update_data(key_access_url=key.access_url)
        await state.set_state(GetKey.sending_key)
    except Exception as e:
        logger.error(f"Произошла ошибка: {e}")
        await message.answer(
            "Произошла ошибка при обработке вашего платежа. Пожалуйста, свяжитесь с поддержкой."
        )
        await state.clear()


def log_payment_details(message: Message):
    """Логирует детали успешного платежа."""
    logger.info(json.dumps(message.dict(), indent=4, default=str))


def create_vpn_key():
    """Создает новый VPN-ключ."""
    keys_lst = outline_processor.get_keys()
    max_id = max([int(key.key_id) for key in keys_lst])
    return outline_processor.create_new_key(
        key_id=max_id + 1, name=f"VPN Key{len(keys_lst) + 1}", data_limit_gb=1
    )


def expiration_date_for_user(user: DbProcessor.User):
    """Возвращает дату окончания ключей для пользователя."""
    expiration_dates = {}
    if not user.keys:
        return None
    expiration_dates = {key: key.expiration_date for key in user.keys}
    return expiration_dates


async def send_key_to_user(message: Message, key, text="Ваш ключ от VPN"):
    """Отправляет созданный ключ пользователю."""
    logger.info(f"Key created: {key} for user {message.from_user.id}")
    await message.answer(
        get_your_key_string(key, text),
        parse_mode="Markdown",
        reply_markup=get_installation_button(),
    )


def get_session():
    return db_processor.Session()


async def update_database_with_key(user_id: int, key, period: str):
    try:
        session = get_session()
        user_id_str = str(user_id)
        user = (
            session.query(DbProcessor.User)
            .filter_by(user_telegram_id=user_id_str)
            .first()
        )
        if not user:
            user = DbProcessor.User(
                user_telegram_id=user_id_str,
                subscription_status="active",
                use_trial_period=False,
            )
            session.add(user)
            session.commit()
        period_months = int(period.split()[0])
        start_date = datetime.now()
        expiration_date = start_date + timedelta(days=30 * period_months)
        new_key = DbProcessor.Key(
            key_id=key.key_id,
            user_telegram_id=user_id_str,
            expiration_date=expiration_date,
            start_date=start_date,
        )
        session.add(new_key)
        session.commit()
    except Exception as e:
        logger.error(f"Ошибка обновления базы данных: {e}")
        raise
    finally:
        session.close()


@router.callback_query(
    F.data == "installation_instructions", StateFilter(GetKey.sending_key)
)
async def send_installation_instructions(callback: CallbackQuery, state: FSMContext):
    # Пример инструкции
    data = await state.get_data()
    key_access_url = data.get("key_access_url", "URL не найден")
    instructions = get_instruction_string(key_access_url)
    await callback.message.answer(
        instructions,
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=get_instruction_keyboard(),
    )

    await callback.answer()
    await state.set_state(default_state)


@router.callback_query(StateFilter(ManageKeys.choosing_key))
async def choosing_key_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Вы в менеджере ключей"
    )

    # await delete_previous_message(callback.message.chat.id, state)

    user_id = callback.from_user.id
    user_id_str = str(user_id)
    session = get_session()

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

            await callback.message.answer(
                key_details,
                reply_markup=back_button()
            )

    except Exception as e:
        logger.error(f"Ошибка при выборе ключа: {e}")
        await callback.message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")
        await state.clear()
    finally:
        session.close()
    await callback.answer()


async def create_trial_key(user_id: int):
    """Создает пробный ключ для пользователя."""
    key = create_vpn_key()
    session = get_session()
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
    session = get_session()

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
        key = create_vpn_key()

        period_months = 0.5
        start_date = datetime.now()
        expiration_date = start_date + timedelta(days=4 * period_months)
        new_key = DbProcessor.Key(
            key_id=key.key_id,
            user_telegram_id=user_id_str,
            expiration_date=expiration_date,
            start_date=start_date,
        )
        session.add(new_key)
        session.commit()

        text = "Ваш пробный ключ готов к использованию. Срок действия - 2 дня."
        await send_key_to_user(callback.message, key, text, reply_markup=back_button())
    else:
        await callback.message.answer(
            "Вы уже использовали пробный период. "
            "Вы можете купить ключ или вернуться в главное меню"
        )
