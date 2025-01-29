from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.initialization.outline_processor_init import outline_processor
from bot.initialization.vless_processor_init import vless_processor
from bot.lexicon.lexicon import get_day_by_number

from logger.log_sender import logger


def get_main_menu_keyboard():
    # Создаем объекты инлайн-кнопок
    get_key = InlineKeyboardButton(
        text="🆕 Получить ключ", callback_data="choice_vpn_type"
    )

    ket_management = InlineKeyboardButton(
        text="🛠️ Менеджер ключей", callback_data="key_management_pressed"
    )

    about_us = InlineKeyboardButton(text="ℹ️ О нас", callback_data="about_us")

    get_instruction = InlineKeyboardButton(
        text="📃 Инструкция по установке", callback_data="get_instruction"
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[[get_key], [ket_management], [get_instruction], [about_us]]
    )


def get_choice_vpn_type_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="VLESS", callback_data="VPNtype_VLESS"),
                InlineKeyboardButton(text="OUTLINE", callback_data="VPNtype_Outline"),
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main_menu")],
        ]
    )


def get_choice_vpn_type_keyboard_for_no_key():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="VLESS", callback_data="VPNtype_VLESS"),
                InlineKeyboardButton(text="OUTLINE", callback_data="VPNtype_Outline"),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад", callback_data="key_management_pressed"
                )
            ],
        ]
    )


def get_device_vless_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🖥 MacOS",
                    callback_data="device_MacOS",
                    url="https://telegra.ph/Instrukciya-po-ustanovke-vless-na-Mac-01-29",
                ),
                InlineKeyboardButton(
                    text="📱 iPhone",
                    callback_data="device_iPhone",
                    url="https://telegra.ph/Instrukciya-po-ustanovke-vless-na-iPhone-01-29",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💻 Windows",
                    callback_data="device_Windows",
                    url="https://telegra.ph/Instrukciya-po-ustanovke-vless-na-Windows-01-29",
                ),
                InlineKeyboardButton(
                    text="📲 Android",
                    callback_data="device_Android",
                    url="https://telegra.ph/Instrukciya-po-ustanovke-vless-na-Android-01-29",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад", callback_data="back_choice_type_for_instruction"
                )
            ],
        ]
    )


def get_device_outline_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🖥 MacOS",
                    callback_data="device_MacOS",
                    url="https://telegra.ph/Instrukciya-po-ustanovke-Otline-na-MacOS-01-29",
                ),
                InlineKeyboardButton(
                    text="📱 iPhone",
                    callback_data="device_iPhone",
                    url="https://telegra.ph/Instrukciya-po-ustanovke-Outline-na-iPhone-01-29",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💻 Windows",
                    callback_data="device_Windows",
                    url="https://telegra.ph/Instrukciya-po-ustanovke-Outline-na-Windows-01-29",
                ),
                InlineKeyboardButton(
                    text="📲 Android",
                    callback_data="device_Android",
                    url="https://telegra.ph/Instrukciya-po-ustanovke-Outline-na-Android-01-29",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад", callback_data="back_choice_type_for_instruction"
                )
            ],
        ]
    )


def get_choice_vpn_type_keyboard_for_trial_period():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="VLESS", callback_data="trial_period_vless"),
                InlineKeyboardButton(
                    text="OUTLINE", callback_data="trial_period_outline"
                ),
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main_menu")],
        ]
    )


def get_about_us_keyboard():
    back_button = InlineKeyboardButton(
        text="🔙 Назад", callback_data="back_to_main_menu"
    )
    return InlineKeyboardMarkup(inline_keyboard=[[back_button]])


def get_period_keyboard():
    # Кнопки для выбора периода
    month_button = InlineKeyboardButton(text="1 Месяц (90₽)", callback_data="1_month")
    three_month_button = InlineKeyboardButton(
        text="3 Месяца (240₽)", callback_data="3_months"
    )
    six_month_button = InlineKeyboardButton(
        text="6 Месяцев (390₽)", callback_data="6_months"
    )
    year_button = InlineKeyboardButton(
        text="12 Месяцев (690₽)", callback_data="12_months"
    )

    trial_period_button = InlineKeyboardButton(
        text="Пробный период", callback_data="trial_period"
    )

    back_button = InlineKeyboardButton(
        text="🔙 Назад", callback_data="back_to_choice_vpn_type"
    )

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
                    text="Инструкция",
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
        text="Пробный ключ", callback_data="get_trial_period"
    )
    buy_key_button = InlineKeyboardButton(
        text="Купить ключ", callback_data="get_keys_pressed"
    )
    back_button = InlineKeyboardButton(
        text="🔙 Назад", callback_data="back_to_main_menu"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[[get_trial_key], [buy_key_button], [back_button]]
    )


def get_back_button():
    # Создаем объекты инлайн-кнопок
    to_main_menu_button = InlineKeyboardButton(
        text="В главное меню", callback_data="back_to_main_menu"
    )
    return InlineKeyboardMarkup(inline_keyboard=[[to_main_menu_button]])


def get_extension_keyboard():
    # Кнопки для продления подписки
    extend_now_button = InlineKeyboardButton(
        text="Продлить сейчас 🔄", callback_data="extension_pressed"
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


def get_extension_periods_keyboard():
    # Кнопки для выбора периода
    month_button = InlineKeyboardButton(text="1 Месяц (90₽)", callback_data="1_month")
    three_month_button = InlineKeyboardButton(
        text="3 Месяца (240₽)", callback_data="3_months"
    )
    six_month_button = InlineKeyboardButton(
        text="6 Месяцев (390₽)", callback_data="6_months"
    )
    year_button = InlineKeyboardButton(
        text="12 Месяцев (690₽)", callback_data="12_months"
    )
    back_button = InlineKeyboardButton(text="🔙 Назад", callback_data="to_key_params")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [month_button],
            [three_month_button],
            [six_month_button],
            [year_button],
            [back_button],
        ]
    )


def get_key_name_choosing_keyboard(keys: list):
    keyboard_buttons = []
    for key in keys:
        match key.protocol_type.lower():
            case "outline":
                key_info = outline_processor.get_key_info(key.key_id)
            case "vless":
                key_info = vless_processor.get_key_info(key.key_id)
        button = InlineKeyboardButton(
            text=f"🔑 {key_info.name}", callback_data=f"key_{key.key_id}"
        )
        keyboard_buttons.append([button])

    back_button = [
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main_menu")
    ]
    keyboard_buttons.append(back_button)

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def get_key_name_extension_keyboard_with_names(keys: dict):
    keyboard_buttons = []
    for key_id in keys:
        days = get_day_by_number(keys[key_id][1])
        button = InlineKeyboardButton(
            text=f"🔑 {keys[key_id][0]} ({keys[key_id][1]} {days})",
            callback_data=f"extend_{key_id}",
        )
        keyboard_buttons.append([button])

    back_button = [
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main_menu")
    ]
    keyboard_buttons.append(back_button)

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def get_key_action_keyboard(key_info):
    view_traffic_button = InlineKeyboardButton(
        text="📊 Посмотреть объем трафика", callback_data=f"traffic_{key_info.key_id}"
    )
    end_data_button = InlineKeyboardButton(
        text="📅 Посмотреть дату конца активации",
        callback_data=f"expiration_{key_info.key_id}",
    )
    extend_key_button = InlineKeyboardButton(
        text="⏳ Продлить действие ключа", callback_data=f"extend_{key_info.key_id}"
    )
    rename_key_button = InlineKeyboardButton(
        text="✏️ Переименовать ключ", callback_data=f"rename_{key_info.key_id}"
    )
    get_url_key_button = InlineKeyboardButton(
        text="🔑 Показать ключ", callback_data=f"access_url_{key_info.key_id}"
    )
    back_button = InlineKeyboardButton(
        text="🔙 Назад", callback_data="key_management_pressed"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [view_traffic_button],
            [end_data_button],
            [extend_key_button],
            [rename_key_button],
            [get_url_key_button],
            [back_button],
        ]
    )


def get_confirmation_keyboard():
    confirm_button = InlineKeyboardButton(
        text="✅ Подтвердить", callback_data="confirm_rename"
    )
    cancel = InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_rename")

    return InlineKeyboardMarkup(inline_keyboard=[[confirm_button], [cancel]])


def get_already_have_trial_key_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 Назад", callback_data=f"back_to_choice_period"
                ),
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
                InlineKeyboardButton(text="🔙 Назад", callback_data="to_key_params"),
                InlineKeyboardButton(
                    text="В главное меню", callback_data="back_to_main_menu"
                ),
            ]
        ]
    )


def get_back_button_to_buy_key(price):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"Оплатить {price}₽", pay=True)],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_buy_key"),
                InlineKeyboardButton(
                    text="В главное меню", callback_data="back_to_main_menu"
                ),
            ],
        ]
    )
