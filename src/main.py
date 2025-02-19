import asyncio
import aiocron

from bot.initialization.bot_init import dp
from bot.initialization.bot_init import bot
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

@aiocron.crontab("0 11,21 * * *")
async def scheduled_check_db():
    await db_processor.check_db()

async def main() -> None:
    logger.info("Регистрация main menu команд...")
    logger.info("Запуск polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен вручную.")
    except Exception as e:
        logger.error(f"Произошла ошибка при запуске бота: {e}")
