from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from outline_vpn.outline_vpn import OutlineKey

from src.bot.initialization.bot_init import bot
from src.bot.keyboards.keyboards import (
    get_back_button_to_key_params,
    get_extension_keyboard,
    get_installation_button,
    get_key_name_extension_keyboard_with_names,
)
from src.bot.lexicon.lexicon import Notification
from src.bot.utils.string_makers import get_your_key_string
from src.logger.logging_config import setup_logger

logger = setup_logger()


async def send_key_to_user(
    message: Message, key: OutlineKey, text: str = "Ваш ключ от VPN"
) -> None:
    """Отправляет ключ пользователю."""
    logger.info(f"Key created: {key} for user {message.from_user.id}")
    await message.edit_text(
        get_your_key_string(key, text),
        parse_mode="Markdown",
        reply_markup=get_installation_button(),
    )


async def send_key_to_user_with_back_button(message: Message, key_info, text: str):
    """Отправляет ключ пользователю c кнопкой назад в параметры ключа"""
    await message.edit_text(
        get_your_key_string(key_info, text),
        parse_mode="Markdown",
        reply_markup=get_back_button_to_key_params(),
    )


async def send_message_and_save(message, text: str, state: FSMContext, **kwargs):
    sent_message = await message.answer(text, **kwargs)
    await state.update_data(previous_message_id=sent_message.message_id)
    return sent_message


async def send_message_subscription_expired(user, keys, keys_id):
    # Клавиатура для продления подписки
    await bot.send_message(
        user.user_telegram_id,
        Notification.SUBSCRIPTION_EXPIRING.value,
        parse_mode="HTML",
        reply_markup=get_key_name_extension_keyboard_with_names(keys, keys_id),
    )


async def send_message_subscription_ends(user):
    await bot.send_message(
        user.user_telegram_id,
        Notification.SUBSCRIPTION_REMINDER.value,
        parse_mode="HTML",
        reply_markup=get_extension_keyboard(),
    )
