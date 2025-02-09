import os

from dotenv import load_dotenv

from bot.processors.vdsina_processor import VDSinaAPI

load_dotenv()
VDSINA_EMAIL = os.getenv("VDSINA_EMAIL")
VDSINA_PASSWORD = os.getenv("VDSINA_PASSWORD")

vdsina_processor = VDSinaAPI()


async def vdsina_processor_init():
    await vdsina_processor.authenticate(VDSINA_EMAIL, VDSINA_PASSWORD)
