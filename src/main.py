import asyncio
import aiocron
import logging
import uvicorn

from fastapi import FastAPI
from servers.redirect_server import redirect_server
from initialization.bot_init import dp, bot
from initialization.db_processor_init import db_processor, main_init_db
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

from logger.logging_config import configure_logging

configure_logging() # конфигурируем логгер для всего

logger = logging.getLogger(__name__)

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

async def run_fastapi_server():
    # Настраиваем uvicorn для работы в том же цикле событий
    config = uvicorn.Config(
        redirect_server,       # наш объект FastAPI()
        host="0.0.0.0",
        port=8000,
        loop="asyncio",        # важно указать, что работаем на asyncio
        log_level="info"
    )
    server = uvicorn.Server(config)
    # Запускаем сервер (он будет «заблокирован» внутри своей задачи)
    await server.serve()

@aiocron.crontab("0 10,21 * * *")
async def scheduled_check_db():
    await db_processor.check_db()

@aiocron.crontab("* * * * *")
async def scheduled_check_db():
    await db_processor.check_and_update_key_data_limit()


async def main() -> None:
    main_init_db()  # инициализируем БД 1ый раз при запуске
    logger.info("Запускаем FastAPI и бота...")
    server_task = asyncio.create_task(run_fastapi_server())
    bot_task = asyncio.create_task(dp.start_polling(bot))
    logger.info("Запуск polling...")
    await asyncio.gather(server_task, bot_task)



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен вручную.")
    except Exception as e:
        logger.error(f"Произошла ошибка при запуске бота: {e}")
