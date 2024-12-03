from aiogram import Bot
import os
from dotenv import load_dotenv
from logger.logging_config import setup_logger
from outline_vpn.outline_vpn import OutlineVPN

load_dotenv()
BOT_TOKEN = os.getenv("TOKEN")
logger = setup_logger()
if not BOT_TOKEN:
    logger.critical("BOT_TOKEN не задан. Проверьте .env файл.")
    exit("Отсутствует BOT_TOKEN")
logger.info("Инициализация бота...")
bot = Bot(token=BOT_TOKEN)

