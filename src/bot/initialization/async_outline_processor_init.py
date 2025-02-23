import os
from dotenv import load_dotenv

from bot.processors.async_outline_processor import OutlineProcessor

load_dotenv()

API_URL = os.getenv("API_URL")
CERT_SHA256 = os.getenv("CERT_SHA")

if not API_URL or not CERT_SHA256:
    raise ValueError("Ошибка: Отсутствуют необходимые переменные окружения API_URL или CERT_SHA.")

async_outline_processor = OutlineProcessor()


