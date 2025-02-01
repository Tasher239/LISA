import os
import asyncio
from dotenv import load_dotenv

from bot.processors.async_outline_processor import OutlineProcessor

load_dotenv()

api_url = os.getenv("API_URL")
cert_sha256 = os.getenv("CERT_SHA")


async_outline_processor = OutlineProcessor(api_url=api_url, cert_sha256=cert_sha256)

async def init_outline_processor():
    await async_outline_processor.init()