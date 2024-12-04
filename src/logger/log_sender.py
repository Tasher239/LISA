import json

from aiogram.types import Message

from logger.logging_config import setup_logger

logger = setup_logger()


class LogSender:
    @staticmethod
    def log_payment_details(message: Message):
        """Логирует детали успешного платежа."""
        logger.info(json.dumps(message.dict(), indent=4, default=str))
