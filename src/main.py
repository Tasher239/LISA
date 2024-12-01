from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, LabeledPrice
from aiogram import F, types
from aiogram.types import CallbackQuery
from aiogram.fsm.state import default_state, State, StatesGroup
from outline_vpn.outline_vpn import OutlineVPN
from bot.keyboards.keyboards import *
from bot.utils.outline_processor import OutlineProcessor
import uuid
import json
import logging
import asyncio
import sys

dp = Dispatcher()
api_url = 'https://5.35.38.7:8811/p78Ho3alpF3e8Sv37eLV1Q'
cert_sha256 = 'CA9E91B93E16E1F160D94D17E2F7C0D0D308858A60F120F6C8C1EDE310E35F64'

client = OutlineVPN(api_url=api_url, cert_sha256=cert_sha256)

outline_processor = OutlineProcessor(client)

BOT_TOKEN = "7444575424:AAGm9XiB3KPYWsI_30ivVO7QAELnIoatcCw"
bot = Bot(token=BOT_TOKEN)

# 'stop_time' - ISO 8601
user_db = [{'user_id': 234, 'stop_time': '01-02-2024', 'use_trial_period': True}]

@dp.message(CommandStart())
async def process_start_command(message: Message):
    await message.answer(
        text='Привет! Добро пожаловать в систему неограниченного '
             'безопасного доступа в Интернет «LISA». Выберите, '
             'что вы хотите сделать',
        reply_markup=main_menu_keyboard
    )

@dp.callback_query(F.data == 'get_keys_pressed')
async def get_key_handler(callback: CallbackQuery):
    # После того как пользователь выбрал "Получить Ключ", покажем кнопки выбора периода
    await callback.message.answer(
        text='Выберите период действия ключа:',
        reply_markup=period_keyboard
    )


@dp.callback_query(F.data.in_(['1_month', '3_months', '6_months', '12_months']))
async def handle_period_selection(callback: CallbackQuery):
    selected_period = callback.data.replace('_', ' ').title()
    provider_token = '401643678:TEST:48ccf303-caed-45b4-ad17-bb35ff180fe7'
    prices = [LabeledPrice(label="Ключ от VPN", amount=10000)]
    match callback.data:
        case '1_month':
            description = 'Ключ от VPN Outline на 1 месяц'
        case '3_months':
            description = 'Ключ от VPN Outline на 3 месяца'
        case '6_months':
            description = 'Ключ от VPN Outline на 6 месяцев'
        case '12_months':
            description = 'Ключ от VPN Outline на 12 месяцев'


    await bot.send_invoice(chat_id=callback.message.chat.id,
                           title='Покупка ключа',
                           description=description,
                           payload=str(uuid.uuid4()),
                           provider_token=provider_token,
                           start_parameter=str(uuid.uuid4()),
                           currency='rub',
                           prices=prices)

# Обработчик предпросмотра платежа
@dp.pre_checkout_query()
async def pre_checkout_query(pre_checkout_q: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)


# Обработчик успешного платежа
@dp.message(lambda message: message.successful_payment)
async def successful_payment(message: types.Message):
    print(json.dumps(message.dict(), indent=4, default=str))
    successful_payment = message.successful_payment
    await message.answer(
        f"Спасибо за покупку! Оплата на сумму {successful_payment.total_amount / 100} {successful_payment.currency} успешно прошла.")

@dp.callback_query(F.data == 'key_management_pressed')
async def process_key_management(callback: CallbackQuery):
    await callback.message.answer(
        'Вы выбрали "Управление ключами".'
    )

async def main() -> None:
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
