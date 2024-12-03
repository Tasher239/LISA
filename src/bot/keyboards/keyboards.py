# keyboards.py
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from numpy.random.mtrand import set_state


def get_main_menu_keyboard():
    # Создаем объекты инлайн-кнопок
    get_key = InlineKeyboardButton(
        text="Получить Ключ", callback_data="get_keys_pressed"
    )

    ket_management = InlineKeyboardButton(
        text="Управление ключами", callback_data="key_management_pressed"
    )

    about_us = InlineKeyboardButton(text="О нас", callback_data="about_us")

    return InlineKeyboardMarkup(
        inline_keyboard=[[get_key], [ket_management], [about_us]]
    )


def get_period_keyboard():
    # Кнопки для выбора периода
    month_button = InlineKeyboardButton(text="1 Месяц (1$)", callback_data="1_month")
    three_month_button = InlineKeyboardButton(
        text="3 Месяца (10$)", callback_data="3_months"
    )
    six_month_button = InlineKeyboardButton(
        text="6 Месяцев (100$)", callback_data="6_months"
    )
    year_button = InlineKeyboardButton(
        text="12 Месяцев (1000$)", callback_data="12_months"
    )

    trial_period_button = InlineKeyboardButton(
        text="Пробный период", callback_data="trial_period"
    )

    back_button = InlineKeyboardButton(text="Назад", callback_data="go_back")

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [month_button],
            [three_month_button],
            [six_month_button],
            [year_button],
            [trial_period_button],
            [back_button],
        ]
    )


def get_installation_button():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Нужна инструкция по установке",
                    callback_data="installation_instructions",
                ),
                InlineKeyboardButton(
                    text="В главное меню",
                    callback_data="to_main_menu",
                ),
            ]
        ]
    )


def get_buttons_for_trial_period():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Получить ключ", callback_data="trial_period"
                ),
                InlineKeyboardButton(text="Назад", callback_data="back_to_main_menu"),
            ]
        ]
    )


# def get_instruction_keyboard():
#     # Создаем объекты инлайн-кнопок
#     to_main_menu_button = InlineKeyboardButton(
#         text="В главное меню", callback_data="to_main_menu"
#     )
#     return InlineKeyboardMarkup(inline_keyboard=[[to_main_menu_button]])


def get_back_button():
    # Создаем объекты инлайн-кнопок
    to_main_menu_button = InlineKeyboardButton(
        text="В главное меню", callback_data="to_main_menu"
    )
    return InlineKeyboardMarkup(inline_keyboard=[[to_main_menu_button]])


def get_prodlit_keyboard():
    # Кнопки для продления подписки
    extend_now_button = InlineKeyboardButton(
        text="Продлить сейчас 🔄", callback_data="extend_now"
    )
    back_to_main_menu_button = InlineKeyboardButton(
        text="В главное меню 🔙", callback_data="to_main_menu"
    )

    # Возвращаем клавиатуру
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [extend_now_button],  # Кнопка "Продлить сейчас"
            [back_to_main_menu_button],  # Кнопка "В главное меню"
        ]
    )

def get_prodlenie_keyboard():
    # Кнопки для выбора периода
    month_button = InlineKeyboardButton(text="1 Месяц (50₽)", callback_data="1_month")
    three_month_button = InlineKeyboardButton(
        text="3 Месяца (140₽)", callback_data="3_months"
    )
    six_month_button = InlineKeyboardButton(
        text="6 Месяцев (270₽)", callback_data="6_months"
    )
    year_button = InlineKeyboardButton(
        text="12 Месяцев (490₽)", callback_data="12_months"
    )

    trial_period_button = InlineKeyboardButton(
        text="Пробный период", callback_data="trial_period"
    )

    back_button = InlineKeyboardButton(text="Назад", callback_data="go_back")

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [month_button],
            [three_month_button],
            [six_month_button],
            [year_button],
            [trial_period_button],
            [back_button],
        ]
    )
