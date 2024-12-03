import json
from logger.logging_config import setup_logger
from aiogram.types import Message

logger = setup_logger()


class LogSender:
    @staticmethod
    def log_payment_details(message: Message):
        """Логирует детали успешного платежа."""
        logger.info(json.dumps(message.dict(), indent=4, default=str))
