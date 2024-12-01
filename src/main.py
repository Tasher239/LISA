import sys
import json
import uuid
import logging
import asyncio

import os
from src.database.user_db import DbProcessor

db_processor = DbProcessor()
session = db_processor.Session()

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from aiogram import F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram import types

from outline_vpn.outline_vpn import OutlineVPN

from bot.keyboards.keyboards import main_menu_keyboard, period_keyboard, get_installation_button
from bot.fsm.states import GetKey
from bot.utils.outline_processor import OutlineProcessor
from dotenv import load_dotenv
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()
api_url = os.getenv('API_URL')
cert_sha256 = os.getenv('CERT_SHA')
client = OutlineVPN(api_url=api_url, cert_sha256=cert_sha256)
outline_processor = OutlineProcessor(client)
BOT_TOKEN = os.getenv('TOKEN')
provider_token = os.getenv('PROVIDER_SBER_TOKEN')
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)


# 'stop_time' - ISO 8601
user_db = [{'user_id': 234, 'stop_time': '01-02-2024', 'use_trial_period': True}]

# Создаем объекты инлайн-кнопок
get_key = InlineKeyboardButton(
    text='•	Получить Ключ',
    callback_data='get_keys_pressed'
)

ket_management = InlineKeyboardButton(
    text='•	Управление ключами',
    callback_data='key_management_pressed'
)

main_menu_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[get_key],
                     [ket_management]]
)

# Кнопки для выбора периода
month_button = InlineKeyboardButton(text='• Месяц (1$)', callback_data='1_month')
three_month_button = InlineKeyboardButton(text='• 3 Месяца (10$)', callback_data='3_months')
six_month_button = InlineKeyboardButton(text='• 6 Месяцев (100$)', callback_data='6_months')
year_button = InlineKeyboardButton(text='• 12 Месяцев (1000$)', callback_data='12_months')

period_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[month_button],
                     [three_month_button],
                     [six_month_button],
                     [year_button]]
)



@dp.message(CommandStart())
async def process_start_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        text='Привет! Добро пожаловать в систему неограниченного '
             'безопасного доступа в Интернет «LISA». Выберите, '
             'что вы хотите сделать',
        reply_markup=main_menu_keyboard
    )


@dp.callback_query(F.data == 'get_keys_pressed')
async def get_key_handler(callback: CallbackQuery, state: FSMContext):
    # После того как пользователь выбрал "Получить Ключ", покажем кнопки выбора периода
    await callback.message.answer(
        text='Выберите период действия ключа:',
        reply_markup=period_keyboard
    )
    await state.set_state(GetKey.choosing_period)


@dp.callback_query(StateFilter(GetKey.choosing_period))
async def handle_period_selection(callback: CallbackQuery, state: FSMContext):
    selected_period = callback.data.replace('_', ' ').title()
    prices = [LabeledPrice(label="Ключ от VPN", amount=10000)]
    description = f'Ключ от VPN Outline на {selected_period}'
    # переходим в состояние ожидания оплаты
    await state.set_state(GetKey.waiting_for_payment)

    await bot.send_invoice(chat_id=callback.message.chat.id,
                           title='Покупка ключа',
                           description=description,
                           payload=str(uuid.uuid4()),
                           provider_token=provider_token,
                           start_parameter=str(uuid.uuid4()),
                           currency='rub',
                           prices=prices)


# Обработчик предпросмотра платежа (пока не понятно зачем нам)
'''
Метод answer_pre_checkout_query() отвечает на запрос Telegram о предварительной проверке платежа.
В pre_checkout_q.id передается уникальный идентификатор запроса, полученный из объекта PreCheckoutQuery.
Параметр ok=True указывает, что запрос на предварительную проверку платежа был принят и все в порядке (платеж можно продолжать).
Если вы хотите отклонить платеж, вы можете установить ok=False и добавить описание причины отклонения через параметр error_message.
'''


@dp.pre_checkout_query()
async def pre_checkout_query(pre_checkout_q: PreCheckoutQuery):
    # Проверяем данные платежа
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

#Обработчик успешного платежа
@dp.message(StateFilter(GetKey.waiting_for_payment), lambda message: message.successful_payment)

async def successful_payment(message: Message, state: FSMContext):
    try:
        logger.info(json.dumps(message.dict(), indent=4, default=str))
        keys_lst = outline_processor.get_keys()
        max_key_id = max([int(key.key_id) for key in keys_lst])
        key = outline_processor.create_new_key(key_id=max_key_id + 1, name=f'VPN Key{max_key_id + 1}', data_limit_gb=1)

        await message.answer(f'Ваш ключ от VPN:\naccess_url: {key.access_url}\npassword: {key.password}')

        logger.info(f'Key created: {key} for user {message.from_user.id}')
        await state.update_data(key_access_url=key.access_url)
        await message.answer(
            f"Ваш ключ от VPN:\n\n"
            f"```\n"
            f"{key.access_url}\n"
            f"```",
            parse_mode="Markdown",
            reply_markup=get_installation_button()
        )

        # Обновление базы данных
        try:
            # Проверка, существует ли пользователь
            user = session.query(DbProcessor.User).filter_by(user_telegram_id=message.from_user.id).first()
            if not user:
                # Если пользователя нет, создаем нового
                user = DbProcessor.User(
                    user_telegram_id=message.from_user.id,
                    subscription_status='active',
                    use_trial_period=False  # Предположительно, пробный период уже использован
                )
                session.add(user)

            # Добавление нового ключа для пользователя
            new_key = DbProcessor.Key(
                key_id=str(max_key_id + 1),
                user_telegram_id=message.from_user.id
            )
            session.add(new_key)

            # Сохранение изменений
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Ошибка обновления базы данных: {e}")
            await message.answer("Произошла ошибка при сохранении данных в базу. Пожалуйста, свяжитесь с поддержкой.")
        finally:
            session.close()

    except Exception as e:
        logger.error(f"Error processing successful payment: {e}")
        await message.answer(
            "Произошла ошибка при обработке вашего заказа. Пожалуйста, свяжитесь с поддержкой: `@mickpear`",
            parse_mode="Markdown"
        )
        await state.clear()

@dp.callback_query(F.data == "installation_instructions")
async def send_installation_instructions(callback: CallbackQuery, state: FSMContext):
    # Пример инструкции
    data = await state.get_data()
    key_access_url = data.get("key_access_url", "URL не найден")
    instructions = (
        "📖 Инструкция по установке VPN:\n\n"
        "1. Скачайте приложение OutLine:\n"
        "   - Для Android: [Ссылка на Google Play](https://play.google.com/store/apps/details?id=org.outline.android.client&hl=ru)\n"
        "   - Для iOS: [Ссылка на App Store](https://apps.apple.com/ru/app/outline-app/id1356177741)\n"
        "   - Для Windows/Mac: [Ссылка на сайт](https://example.com)\n\n"
        "2. Откройте приложение и введите следующие данные:\n"
        f"```\n"
        f"{key_access_url}\n"
        f"```"
        "3. Подключитесь и наслаждайтесь безопасным интернетом! 🎉"
    )
    await callback.message.answer(instructions, parse_mode="Markdown", disable_web_page_preview=True)
    await callback.answer()
    await state.clear()





@dp.callback_query(F.data == 'key_management_pressed')
async def process_key_management(callback: CallbackQuery):
    await callback.message.answer(
        'Вы выбрали "Управление ключами".'
    )

async def main() -> None:
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())


