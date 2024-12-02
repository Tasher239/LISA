import json
import uuid

import os
from database.user_db import DbProcessor

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
)
from bot.fsm.states import GetKey

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


@router.message(CommandStart())
async def process_start_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        text="Привет! Добро пожаловать в систему неограниченного "
        "безопасного доступа в Интернет «LISA». Выберите, "
        "что вы хотите сделать",
        reply_markup=get_main_menu_keyboard(),
    )


@router.callback_query(F.data == "get_keys_pressed")
async def get_key_handler(callback: CallbackQuery, state: FSMContext):
    # После того как пользователь выбрал "Получить Ключ", покажем кнопки выбора периода
    await callback.message.answer(
        text="Выберите период действия ключа:", reply_markup=get_period_keyboard()
    )
    await state.set_state(GetKey.choosing_period)


@router.callback_query(StateFilter(GetKey.choosing_period))
async def handle_period_selection(callback: CallbackQuery, state: FSMContext):
    selected_period = callback.data.replace("_", " ").title()
    amount = prices_dict[selected_period.split()[0]]
    prices = [LabeledPrice(label="Ключ от VPN", amount=amount)]
    description = f"Ключ от VPN Outline на {selected_period}"

    # переходим в состояние ожидания оплаты
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
        await update_database_with_key(message.from_user.id, key)

        await state.update_data(key_access_url=key.access_url)

    except Exception as e:
        logger.error(f"Произошла ошибка: {e}")
        await message.answer(
            "Произошла ошибка при обработке вашего платежа. Пожалуйста, свяжитесь с поддержкой."
        )


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


async def send_key_to_user(message: Message, key):
    """Отправляет созданный ключ пользователю."""
    logger.info(f"Key created: {key} for user {message.from_user.id}")
    await message.answer(
        get_your_key_string(key),
        parse_mode="Markdown",
        reply_markup=get_installation_button(),
    )


def get_session():
    return db_processor.Session()

async def update_database_with_key(user_id: int, key):
    try:
        with get_session() as session:
            user = session.query(DbProcessor.User).filter_by(user_telegram_id=user_id).first()
            if not user:
                user = DbProcessor.User(
                    user_telegram_id=user_id,
                    subscription_status="active",
                    use_trial_period=False,
                )
                session.add(user)
            new_key = DbProcessor.Key(key_id=key.key_id, user_telegram_id=user_id)
            session.add(new_key)
            session.commit()
    except Exception as e:
        logger.error(f"Ошибка обновления базы данных: {e}")
        raise

@router.callback_query(F.data == "installation_instructions")
async def send_installation_instructions(callback: CallbackQuery, state: FSMContext):
    # Пример инструкции
    data = await state.get_data()
    key_access_url = data.get("key_access_url", "URL не найден")
    instructions = get_instruction_string(key_access_url)
    await callback.message.answer(
        instructions, parse_mode="Markdown", disable_web_page_preview=True
    )
    await callback.answer()
    await state.clear()


@router.callback_query(F.data == "key_management_pressed")
async def process_key_management(callback: CallbackQuery):
    await callback.message.answer('Вы выбрали "Управление ключами".')
