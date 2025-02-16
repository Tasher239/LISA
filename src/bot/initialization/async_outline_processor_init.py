import os
from dotenv import load_dotenv

from bot.processors.async_outline_processor import OutlineProcessor

load_dotenv()

api_url = os.getenv("API_URL")
cert_sha256 = os.getenv("CERT_SHA")


async_outline_processor = OutlineProcessor()
