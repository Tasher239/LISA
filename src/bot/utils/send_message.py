from bot.utils.string_makers import get_your_key_string
from aiogram.types import Message
from logger.logging_config import setup_logger
from bot.keyboards.keyboards import (
    get_installation_button,
)
from aiogram.fsm.context import FSMContext

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
