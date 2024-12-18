from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.bot.keyboards.keyboards import get_installation_button

from src.bot.initialization.bot_init import bot
from src.bot.keyboards.keyboards import get_prodlit_keyboard
from src.bot.lexicon.lexicon import Notification
from src.bot.utils.string_makers import get_your_key_string

from src.logger.logging_config import setup_logger

logger = setup_logger()


async def send_key_to_user(message: Message, key, text="Ваш ключ от VPN"):
    """Отправляет созданный ключ пользователю."""
    logger.info(f"Key created: {key} for user {message.from_user.id}")
    await message.answer(
        get_your_key_string(key, text),
        parse_mode="Markdown",
        reply_markup=get_installation_button(),
    )


async def send_message_and_save(message, text, state: FSMContext, **kwargs):
    sent_message = await message.answer(text, **kwargs)
    await state.update_data(previous_message_id=sent_message.message_id)
    return sent_message


async def send_message_subscription_expired(user):
    await bot.send_message(
        user.user_telegram_id,
        Notification.SUBSCRIPTION_EXPIRED.value,
        parse_mode="HTML",
        reply_markup=get_prodlit_keyboard(),  # Клавиатура для продления подписки
    )


async def send_message_subscription_ends(user):
    await bot.send_message(
        user.user_telegram_id,
        Notification.SUBSCRIPTION_REMINDER.value,
        parse_mode="HTML",
        reply_markup=get_prodlit_keyboard(),
    )
