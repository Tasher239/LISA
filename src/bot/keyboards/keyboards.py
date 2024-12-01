# keyboards.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice

def main_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Получить Ключ"))
    keyboard.add(KeyboardButton("Управление ключами"))
    return keyboard

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

def get_installation_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Нужна инструкция по установке", callback_data="installation_instructions")]
    ])