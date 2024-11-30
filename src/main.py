from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram import F
from aiogram.types import CallbackQuery
from aiogram.fsm.state import default_state, State, StatesGroup

from bot.utils.outline_processor import OutlineProcessor

api_url = 'https://5.35.38.7:8811/p78Ho3alpF3e8Sv37eLV1Q'
cert_sha256 = 'CA9E91B93E16E1F160D94D17E2F7C0D0D308858A60F120F6C8C1EDE310E35F64'

client = OutlineVPN(api_url=api_url, cert_sha256=cert_sha256)

outline_processor = OutlineProcessor(client)

BOT_TOKEN = "7444575424:AAGm9XiB3KPYWsI_30ivVO7QAELnIoatcCw"

# Создаем объекты бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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
    # Здесь можно обработать выбранный период
    selected_period = callback.data.replace('_', ' ').title()

    await callback.message.answer(
        text=f'Вы выбрали: {selected_period}. Спасибо за выбор!'
    )


@dp.callback_query(F.data == 'key_management_pressed')
async def process_key_management(callback: CallbackQuery):
    await callback.message.answer(
        'Вы выбрали "Управление ключами".'
    )


if __name__ == '__main__':
    dp.run_polling(bot)