from aiogram import types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram import Dispatcher
from datetime import datetime

# Главная клавиатура
def main_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Получить Ключ"))
    keyboard.add(KeyboardButton("Управление ключами"))
    return keyboard

# Функция для отправки главного меню
async def start_cmd(msg: types.Message):
    await msg.answer("Привет! Добро пожаловать в систему неограниченного безопасного доступа в Интернет «LISA». Выберите, что вы хотите сделать:", reply_markup=main_menu_keyboard())

# Клавиатура для выбора периода действия ключа
def subscription_period_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Месяц (1$)"))
    keyboard.add(KeyboardButton("3 Месяца (10$)"))
    keyboard.add(KeyboardButton("6 Месяцев (100$)"))
    keyboard.add(KeyboardButton("12 Месяцев (1000$)"))
    return keyboard

# Обработчик команды /start
async def on_start(msg: types.Message):
    await msg.answer("Выберите действие:", reply_markup=main_menu_keyboard())

# Обработчик для получения ключа
async def get_key(msg: types.Message):
    await msg.answer("Выберите период действия ключа:", reply_markup=subscription_period_keyboard())

# Функция для обработки нажатий на кнопки
async def handle_button(msg: types.Message):
    if msg.text == "Получить Ключ":
        await get_key(msg)
    elif msg.text == "Управление ключами":
        # Здесь будет логика управления ключами
        pass

# Регистрация обработчиков
def setup_handlers(dp: Dispatcher):
    dp.register_message_handler(on_start, commands="start")
    dp.register_message_handler(handle_button)
