# keyboards.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Получить Ключ"))
    keyboard.add(KeyboardButton("Управление ключами"))
    return keyboard
