import asyncio
import aiocron
import logging
import uvicorn

from fastapi import FastAPI
from servers.redirect_server import redirect_server
from initialization.bot_init import dp, bot
from initialization.vdsina_processor_init import vdsina_processor_init
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
        host="192.168.160.1",
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

@aiocron.crontab("0 * * * *")
async def scheduled_update_key_data_limit():
    await db_processor.check_and_update_key_data_limit()

@aiocron.crontab("*/5 * * * *")
async def scheduled_check_servers():
    await db_processor.check_count_keys_on_servers()



async def main() -> None:
    await vdsina_processor_init()  # инициализируем VDSina API
    main_init_db()  # инициализируем БД 1ый раз при запуске
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
