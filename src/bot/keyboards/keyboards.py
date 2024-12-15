from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from src.bot.initialization.outline_processor_init import outline_processor


def get_main_menu_keyboard():
    # Создаем объекты инлайн-кнопок
    get_key = InlineKeyboardButton(
        text="Получить ключ", callback_data="get_keys_pressed"
    )

    ket_management = InlineKeyboardButton(
        text="Менеджер ключей", callback_data="key_management_pressed"
    )

    about_us = InlineKeyboardButton(text="О нас", callback_data="about_us")

    return InlineKeyboardMarkup(
        inline_keyboard=[[get_key], [ket_management], [about_us]]
    )


def get_about_us_keyboard():
    back_button = InlineKeyboardButton(text="Назад", callback_data="back_to_main_menu")
    return InlineKeyboardMarkup(inline_keyboard=[[back_button]])


def get_period_keyboard():
    # Кнопки для выбора периода
    month_button = InlineKeyboardButton(text="1 Месяц (60₽)", callback_data="1_month")
    three_month_button = InlineKeyboardButton(
        text="3 Месяца (120₽)", callback_data="3_months"
    )
    six_month_button = InlineKeyboardButton(
        text="6 Месяцев (1000₽)", callback_data="6_months"
    )
    year_button = InlineKeyboardButton(
        text="12 Месяцев (1200₽)", callback_data="12_months"
    )

    trial_period_button = InlineKeyboardButton(
        text="Пробный период", callback_data="trial_period"
    )

    back_button = InlineKeyboardButton(text="Назад", callback_data="back_to_main_menu")

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
                    text="Установка",
                    callback_data="installation_instructions",
                ),
                InlineKeyboardButton(
                    text="В главное меню",
                    callback_data="back_to_main_menu",
                ),
            ]
        ]
    )

# это нужно переименовать тк юзается еще в менеджере когда нет активных ключей
def get_buttons_for_trial_period():
    get_trial_key = InlineKeyboardButton(
        text="Пробный ключ", callback_data="trial_period"
    )
    buy_key_button = InlineKeyboardButton(
        text="Купить ключ", callback_data="get_keys_pressed"
    )
    back_button = InlineKeyboardButton(text="Назад", callback_data="back_to_main_menu")

    return InlineKeyboardMarkup(
        inline_keyboard=[[get_trial_key], [buy_key_button], [back_button]]
    )


def get_back_button():
    # Создаем объекты инлайн-кнопок
    to_main_menu_button = InlineKeyboardButton(
        text="В главное меню", callback_data="back_to_main_menu"
    )
    return InlineKeyboardMarkup(inline_keyboard=[[to_main_menu_button]])


def get_prodlit_keyboard():
    # Кнопки для продления подписки
    extend_now_button = InlineKeyboardButton(
        text="Продлить сейчас 🔄", callback_data="extend_now"
    )
    back_to_main_menu_button = InlineKeyboardButton(
        text="В главное меню 🔙", callback_data="back_to_main_menu"
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

    back_button = InlineKeyboardButton(text="Назад", callback_data="back_to_main_menu")

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


def get_key_name_choosing_keyboard(keys):
    keyboard_buttons = []

    for key in keys:
        key_info = outline_processor.get_key_info(key.key_id)
        button = InlineKeyboardButton(
            text=key_info.name, callback_data=f"key_{key.key_id}"
        )
        keyboard_buttons.append([button])

    back_button = [
        InlineKeyboardButton(text="Назад", callback_data="back_to_main_menu")
    ]
    keyboard_buttons.append(back_button)

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def get_key_action_keyboard(key_info):
    view_traffic_button = InlineKeyboardButton(
        text="Посмотреть объем трафика", callback_data=f"traffic_{key_info.key_id}"
    )
    end_data_button = InlineKeyboardButton(
        text="Посмотреть дату конца активации",
        callback_data=f"expiration_{key_info.key_id}",
    )
    prodlit_key_button = InlineKeyboardButton(
        text="Продлить действие ключа", callback_data=f"extend_{key_info.key_id}"
    )
    rename_key_button = InlineKeyboardButton(
        text="Переименовать ключ", callback_data=f"rename_{key_info.key_id}"
    )
    get_url_key_button = InlineKeyboardButton(
        text="Вывести сам ключ", callback_data=f"access_url_{key_info.key_id}"
    )
    back_button = InlineKeyboardButton(
        text="Назад", callback_data="key_management_pressed"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [view_traffic_button],
            [end_data_button],
            [prodlit_key_button],
            [rename_key_button],
            [get_url_key_button],
            [back_button],
        ]
    )


def get_confirmation_keyboard():
    confirm_button = InlineKeyboardButton(
        text="Подтвердить", callback_data="confirm_rename"
    )
    cancel = InlineKeyboardButton(text="Отменить", callback_data="cancel_rename")

    return InlineKeyboardMarkup(inline_keyboard=[[confirm_button], [cancel]])


def get_no_trial_period():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Приобрести ключ", callback_data="get_keys_pressed"
                ),
                InlineKeyboardButton(text="Назад", callback_data="back_to"),
            ]
        ]
    )


def get_already_have_trial_key():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Назад", callback_data="get_keys_pressed"),
                InlineKeyboardButton(
                    text="В главное меню", callback_data="back_to_main_menu"
                ),
            ]
        ]
    )

def get_back_button_to_key_params():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Назад", callback_data="to_key_params"),
                InlineKeyboardButton(
                    text="В главное меню", callback_data="back_to_main_menu"
                ),
            ]
        ]
    )