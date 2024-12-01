from telegram import LabeledPrice, Bot
import uuid
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram import F
from aiogram.types import CallbackQuery
from aiogram.fsm.state import default_state, State, StatesGroup



BOT_TOKEN = "6588698079:AAGO6GIAWPzzmeKukVZgofz33iOQJ32gy94"

# Создаем объекты бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# Этот хэндлер будет срабатывать на команду "/start"
@dp.message(Command(commands=["start"]))
async def process_start_command(message: Message):
    chat_id = message.chat.id
    title = 'selected_period'
    description = 'Описание'
    payload = str(uuid.uuid4())
    provider_token = '401643678:TEST:e41a0523-f49d-4234-aa5f-18494b908082'
    start_parameter = 'start'
    currency = 'RUB'  # Валюта
    prices = [LabeledPrice('Цена', 10000)]  # Цена в копейках

    await bot.send_invoice(chat_id, title, description, payload, provider_token, start_parameter, currency, prices)



# Этот хэндлер будет срабатывать на команду "/help"
@dp.message(Command(commands=['help']))
async def process_help_command(message: Message):
    await message.answer(
        'Напиши мне что-нибудь и в ответ '
        'я пришлю тебе твое сообщение'
    )


# Этот хэндлер будет срабатывать на любые ваши текстовые сообщения,
# кроме команд "/start" и "/help"
@dp.message()
async def send_echo(message: Message):
    await message.reply(text=message.text)


if __name__ == '__main__':
    dp.run_polling(bot)

