from datetime import datetime
import os
import json
import logging

from aiogram.types import FSInputFile
from initialization.bot_init import bot

logger = logging.getLogger(__name__)

try:
    admin_ids_str = os.getenv("ADMIN_IDS", "[]")
    ADMIN_IDS = list(map(int, json.loads(admin_ids_str)))
except Exception as e:
    logger.error(f"Ошибка загрузки ADMIN_IDS: {e}")
    ADMIN_IDS = []


async def send_error_report(error: Exception, log_file_path: str = "logger/bot.log"):
    """
    Рассылает администраторам сообщение с информацией об ошибке и прикрепляет лог-файл.

    :param error: Произошедшая ошибка (Exception).
    :param log_file_path: Путь к файлу логов (по умолчанию "logger/bot.log").
    """
    error_text = (
        f"🚨 *Ошибка на сервере:*\n"
        f"`{error}`\n"
        f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    for admin_id in ADMIN_IDS:
        try:
            # Отправляем сообщение с текстом ошибки
            await bot.send_message(admin_id, error_text, parse_mode="Markdown")
            # Если лог-файл существует, отправляем его как документ
            if os.path.exists(log_file_path):
                log_file = FSInputFile(log_file_path)
                await bot.send_document(admin_id, document=log_file, caption="Лог-файл")
        except Exception as ex:
            logger.error(f"Не удалось отправить сообщение админу {admin_id}: {ex}")
