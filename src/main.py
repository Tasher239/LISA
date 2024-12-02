from aiogram.fsm.storage.memory import MemoryStorage
from bot.handlers import handlers
from aiogram import Dispatcher
from bot.logger.logging_config import setup_logger
import asyncio
from aiogram import Bot, Dispatcher
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("TOKEN")

bot = Bot(token=BOT_TOKEN)

logger = setup_logger()
logger.info("Приложение запущено.")

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Регистрируем роутеры в диспетчере
dp.include_router(handlers.router)


async def main() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
