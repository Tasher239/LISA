from aiogram.fsm.storage.memory import MemoryStorage

# from bot.handlers import handlers
from bot.routers import (
    payment_router,
    main_menu_router,
    key_management_router,
    admins_router,
    reminder_router,
    key_params_router,
    buy_key_router,
    trial_period_router,
    back_button_router,
    utils_router,
)
from logger.logging_config import setup_logger
from aiogram import Dispatcher
from bot.initialization.bot_init import bot  # инициализируем бота
import asyncio
from bot.initialization.db_processor_init import db_processor

logger = setup_logger()

logger.info("Инициализация хранилища состояний (MemoryStorage)...")
storage = MemoryStorage()
logger.info("Инициализация диспетчера...")
dp = Dispatcher(storage=storage)
logger.info("Регистрация обработчиков...")

dp.include_router(main_menu_router.router)
dp.include_router(payment_router.router)
dp.include_router(key_management_router.router)
dp.include_router(buy_key_router.router)

# dp.include_router(handlers.router)

dp.include_router(reminder_router.router)
dp.include_router(key_params_router.router)
dp.include_router(trial_period_router.router)
dp.include_router(back_button_router.router)
dp.include_router(utils_router.router)


async def main() -> None:
    logger.info("Запуск polling...")
    asyncio.create_task(db_processor.check_db())
    # await set_main_menu(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен вручную.")
    except Exception as e:
        logger.error(f"Произошла ошибка при запуске бота: {e}")
