import asyncio

from bot.initialization.bot_init import dp
from bot.initialization.bot_init import bot
from bot.initialization.async_outline_processor_init import init_outline_processor
from bot.initialization.db_processor_init import db_processor
from bot.routers import (
    admin_router,
    buy_key_router,
    key_management_router,
    key_params_router,
    main_menu_router,
    payment_router,
    trial_period_router,
    utils_router,
    choice_vpn_type_router,
)

from logger.logging_config import setup_logger

logger = setup_logger()

logger.info("Регистрация обработчиков...")
dp.include_router(main_menu_router.router)
dp.include_router(payment_router.router)
dp.include_router(key_management_router.router)
dp.include_router(buy_key_router.router)
dp.include_router(key_params_router.router)
dp.include_router(trial_period_router.router)
dp.include_router(utils_router.router)
dp.include_router(choice_vpn_type_router.router)
dp.include_router(admin_router.router)


async def main() -> None:
    logger.info("Регистрация main menu команд...")
    await init_outline_processor()
    logger.info("Запуск polling...")
    asyncio.create_task(
        db_processor.check_db(dp)
    )  # Запуск фоновой проверки базы данных
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен вручную.")
    except Exception as e:
        logger.error(f"Произошла ошибка при запуске бота: {e}")
