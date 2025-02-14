import asyncio

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from bot.initialization.bot_init import dp
from bot.initialization.bot_init import bot
from bot.initialization.async_outline_processor_init import init_outline_processor
from bot.initialization.db_processor_init import db_processor
from bot.routers import (
    admins_router,
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


async def set_main_menu(bot: Bot):
    pass
    # main_menu_commands = [
    #     BotCommand(command="/start", description="Перезапустить бота")
    # ]
    # try:
    #     await bot.delete_my_commands()  # Удаляем старые команды
    #     await bot.set_my_commands(main_menu_commands)  # Устанавливаем новые
    #     logger.info("Команды успешно установлены")
    # except Exception as e:
    #     logger.error(f"Ошибка при установке команд: {e}")


async def main() -> None:
    logger.info("Регистрация main menu команд...")
    await set_main_menu(bot)  # Вызываем set_main_menu напрямую до запуска polling
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
