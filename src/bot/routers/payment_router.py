import os
import uuid

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from dotenv import load_dotenv

from bot.fsm.states import GetKey
from bot.initialization.bot_init import bot
from bot.initialization.db_processor_init import db_processor
from bot.initialization.outline_processor_init import outline_processor
from bot.initialization.vless_processor_init import vless_processor

from bot.keyboards.keyboards import (
    get_back_button,
    get_back_button_to_buy_key,
    get_already_have_trial_key,
)
from bot.utils.dicts import prices_dict
from bot.utils.extend_key_in_db import extend_key_in_db
from bot.utils.send_message import send_key_to_user
from database.db_processor import DbProcessor
from logger.log_sender import LogSender
from logger.logging_config import setup_logger

load_dotenv()
provider_token = os.getenv("PROVIDER_PAYMENT_TOKEN")

router = Router()
logger = setup_logger()

"""
Метод answer_pre_checkout_query() отвечает на запрос Telegram о предварительной проверке платежа.
В pre_checkout_q.id передается уникальный идентификатор запроса, полученный из объекта PreCheckoutQuery.
Параметр ok=True указывает, что запрос на предварительную проверку платежа был принят и все в порядке (платеж можно продолжать).
Если вы хотите отклонить платеж, вы можете установить ok=False и добавить описание причины отклонения через параметр error_message.
"""


@router.callback_query(StateFilter(GetKey.buy_key), ~F.data.in_(["trial_period", "back_to_choice_vpn_type"]))
@router.callback_query(StateFilter(GetKey.choice_extension_period),
                       ~F.data.in_(["to_key_params", "back_to_choice_vpn_type"]))
async def handle_period_selection(callback: CallbackQuery, state: FSMContext):
    selected_period = callback.data.replace("_", " ").title()

    amount = prices_dict[selected_period.split()[0]]
    prices = [LabeledPrice(label="Ключ от VPN", amount=amount)]
    description = f"Ключ от VPN Outline на {selected_period}"

    # Сохранение выбранного периода в состоянии
    await state.update_data(selected_period=selected_period)
    current_state = await state.get_state()
    if current_state == GetKey.buy_key:
        await state.set_state(GetKey.waiting_for_payment)
    else:
        await state.set_state(GetKey.waiting_for_extension_payment)
        await state.update_data(selected_period=selected_period)

    logger.info(f"Sending invoice with currency=RUB, amount={prices}")
    payment_message = await callback.message.edit_text(text="Оплата")
    await state.update_data(payment_message_id=payment_message.message_id)

    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="Покупка ключа",
        description=description,
        payload=str(uuid.uuid4()),
        provider_token=provider_token,
        start_parameter=str(uuid.uuid4()),
        currency="rub",
        prices=prices,
        reply_markup=get_back_button_to_buy_key(amount / 100),
    )

    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout_query(pre_checkout_q: PreCheckoutQuery):
    # Проверяем данные платежа
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)


# Обработчик успешного платежа при ПОКУПКИ ключа
@router.message(
    StateFilter(GetKey.waiting_for_payment), lambda message: message.successful_payment
)
async def successful_payment(message: Message, state: FSMContext):
    try:
        # Логирование успешного платежа
        LogSender.log_payment_details(message)
        # Создание нового ключа VPN
        data = await state.get_data()
        print(data.get("vpn_type"))
        match data.get("vpn_type"):
            case 'Outline':
                processor = outline_processor
                protocol_type = 'Outline'
            case 'VLESS':
                processor = vless_processor
                protocol_type = 'VLESS'

        key = processor.create_vpn_key()

        logger.info(f"Key created: {key} for user {message.from_user.id}")

        new_message = await message.answer(text="Оплата прошла успешно")
        await send_key_to_user(
            new_message, key, text=f"Ваш ключ «{key.name}» добавлен в менеджер ключей"
        )

        # Обновление базы данных
        data = await state.get_data()
        period = data.get("selected_period")
        db_processor.update_database_with_key(message.from_user.id, key, period, protocol_type)

        # Отправка инструкций по установке
        await state.update_data(key_access_url=key.access_url)
        await state.set_state(GetKey.sending_key)
    except Exception as e:
        logger.error(f"Произошла ошибка: {e}")
        await message.answer(
            "Произошла ошибка при создании ключа. Пожалуйста, свяжитесь с поддержкой."
        )
        await state.clear()


# Обработчик успешного платежа при продлении ключа
@router.message(
    StateFilter(GetKey.waiting_for_extension_payment),
    lambda message: message.successful_payment,
)
async def successful_payment(message: Message, state: FSMContext):
    try:
        # Логирование успешного платежа
        LogSender.log_payment_details(message)
        session = db_processor.get_session()
        # Находим ключ по его ID
        data = await state.get_data()
        key_id = data.get("selected_key_id")
        add_period = int(data.get("selected_period").split()[0])
        add_period = 31 * add_period
        new_message = await message.answer(text="Оплата прошла успешно")
        extend_key_in_db(key_id=key_id, add_period=add_period)

        key = session.query(DbProcessor.Key).filter_by(key_id=key_id).first()
        await new_message.edit_text(
            f'Ключ «{outline_processor.get_key_info(key_id).name}» действует до <b>{key.expiration_date.strftime("%d.%m.%y")}</b>',
            parse_mode="HTML",
            reply_markup=get_back_button(),
        )
        await state.set_state(GetKey.sending_key)
    except Exception as e:
        logger.info(e)
