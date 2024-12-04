import os
from dotenv import load_dotenv

from aiogram import F, Router
from aiogram.types import Message, PreCheckoutQuery, LabeledPrice, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.fsm.states import GetKey
from bot.initialization.outline_processor_init import outline_processor
from bot.initialization.bot_init import bot
from bot.initialization.db_processor_init import db_processor
from bot.utils.send_message import send_key_to_user
from bot.utils.dicts import prices_dict_prodl

from logger.log_sender import LogSender
from logger.logging_config import setup_logger

load_dotenv()
provider_token = os.getenv("PROVIDER_SBER_TOKEN")

router = Router()
logger = setup_logger()

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
        LogSender.log_payment_details(message)
        # Создание нового ключа VPN
        key = outline_processor.create_vpn_key()

        logger.info(f"Key created: {key} for user {message.from_user.id}")

        await send_key_to_user(message, key)

        # Обновление базы данных
        data = await state.get_data()
        period = data.get("selected_period", "1 Month")
        db_processor.update_database_with_key(message.from_user.id, key, period)

        # Отправка инструкций по установке
        await state.update_data(key_access_url=key.access_url)
        await state.set_state(GetKey.sending_key)
    except Exception as e:
        logger.error(f"Произошла ошибка: {e}")
        await message.answer(
            "Произошла ошибка при обработке вашего платежа. Пожалуйста, свяжитесь с поддержкой."
        )
        await state.clear()


@router.callback_query(StateFilter(GetKey.prodlenie), F.data != "trial_period")
async def handle_period_selection(callback: CallbackQuery, state: FSMContext):
    # await delete_previous_message(callback.message.chat.id, state)
    selected_period = callback.data.replace("_", " ").title()
    amount = prices_dict_prodl[selected_period.split()[0]]
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
