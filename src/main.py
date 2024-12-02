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
logger = setup_logger()
if not BOT_TOKEN:
    logger.critical("BOT_TOKEN не задан. Проверьте .env файл.")
    exit("Отсутствует BOT_TOKEN")

logger.info("Инициализация бота...")
bot = Bot(token=BOT_TOKEN)
logger.info("Инициализация хранилища состояний (MemoryStorage)...")
storage = MemoryStorage()
logger.info("Инициализация диспетчера...")
dp = Dispatcher(storage=storage)
logger.info("Регистрация обработчиков...")
dp.include_router(handlers.router)

async def main() -> None:
    logger.info("Запуск polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен вручную.")
    except Exception as e:
        logger.error(f"Произошла ошибка при запуске бота: {e}")