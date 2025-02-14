import os

from aiogram import Bot
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Dispatcher
from dotenv import load_dotenv


from src.logger.logging_config import setup_logger

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
