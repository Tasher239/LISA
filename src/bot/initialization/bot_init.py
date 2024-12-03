from aiogram import Bot
import os
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
