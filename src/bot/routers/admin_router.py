from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import json

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.filters import Command
from aiogram import Router, F

from bot.initialization.async_outline_processor_init import async_outline_processor
from bot.initialization.vdsina_processor_init import vdsina_processor
from bot.initialization.vless_processor_init import vless_processor
from bot.initialization.db_processor_init import db_processor
from bot.utils.string_makers import get_your_key_string
from bot.initialization.bot_init import bot
from bot.fsm.states import AdminAccess
from bot.keyboards.keyboards import (
    get_admin_keyboard,
    get_back_button,
    get_back_admin_panel_keyboard,
)

from logger.logging_config import setup_logger

load_dotenv()
router = Router()
logger = setup_logger()

load_dotenv()

admin_passwords = json.loads(os.getenv("ADMIN_PASSWORDS"))
admin_passwords = {int(k): v for k, v in admin_passwords.items()}

pending_admin = {}


@router.message(Command("admin"))
async def admin_start(message: Message, state: FSMContext):
    await message.delete()
    if message.from_user.id in admin_passwords:
        pending_admin[message.from_user.id] = True

        data = await state.get_data()
        prompt_msg_id = data.get("prompt_msg_id")

        new_prompt = await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=prompt_msg_id,
            text="🔒 Введите пароль для доступа к админ-панели.",
            reply_markup=get_back_button(),
        )

        await state.update_data(prompt_msg_id=new_prompt.message_id)
        await state.set_state(AdminAccess.wait_password_enter)
    else:
        await message.answer("🚫 У вас нет доступа.", reply_markup=get_back_button())


@router.message(StateFilter(AdminAccess.wait_password_enter))
async def admin_auth(message: Message, state: FSMContext):
    # Удаляем сообщение с введённым паролем
    await message.delete()

    if pending_admin.get(message.from_user.id):
        # Извлекаем id исходного сообщения с запросом пароля из состояния
        data = await state.get_data()
        prompt_msg_id = data.get("prompt_msg_id")
        if message.text == admin_passwords[message.from_user.id]:
            if prompt_msg_id:
                try:
                    await bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=prompt_msg_id,
                        text="👑 Добро пожаловать в Админ-панель",
                        reply_markup=get_admin_keyboard(),
                    )
                except TelegramBadRequest as e:
                    if "message is not modified" in str(e):
                        # Сообщение не изменилось – игнорируем ошибку
                        pass
                    else:
                        raise
            await state.set_state(AdminAccess.correct_password)
            pending_admin.pop(message.from_user.id, None)
        else:
            try:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=prompt_msg_id,
                    text="🚫 Неверный пароль. Попробуйте снова или вернитесь в главное меню",
                    reply_markup=get_back_button(),
                )
            except TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    # Сообщение не изменилось – игнорируем ошибку
                    pass
                else:
                    raise


async def make_servers_info_text(servers):
    servers_info = "Информация по серверам за послдение 30 дней:\n\n"
    for server in servers:
        servers_info += f"Информация по серверу «{server}»:\n"
        servers_info += await make_info(servers[server]) + "\n\n"
    return servers_info


async def make_info(server):
    virtual_traffic_in_tb = server["vnet_rx"] // 1000
    virtual_traffic_in_gb = server["vnet_rx"] % 1000
    virtual_traffic_out_tb = server["vnet_tx"] // 1000
    virtual_traffic_out_gb = server["vnet_tx"] % 1000

    if virtual_traffic_in_tb > 0:
        virtual_traffix_in_text = (
            f"{virtual_traffic_in_tb:.1f} Тб, {virtual_traffic_in_gb:.1f} Гб"
        )
    else:
        virtual_traffix_in_text = f"{virtual_traffic_in_gb:.1f} Гб"

    if virtual_traffic_out_tb > 0:
        virtual_traffix_out_text = (
            f"{virtual_traffic_out_tb:.1f} Тб, {virtual_traffic_out_gb:.1f} Гб"
        )
    else:
        virtual_traffix_out_text = f"{virtual_traffic_out_gb:.1f} Гб"

    return f"""
Средняя в час загрузка CPU: {server["cpu"]:.1f}%
Дисковые операции: 
    - чтение: {server["disk_reads"]}
    - запись: {server["disk_writes"]}
Трафик виртуальной сети:
    - входящий: {virtual_traffix_in_text}
    - исходящий: {virtual_traffix_out_text}
Сетевой трафик:
    - входящий: {server["lnet_rx"]:.2f} Гб
    - исходящий: {server["lnet_tx"]:.2f} Гб
"""


async def aggregate_statistics(response):
    # Ключи, значения которых можно суммировать
    keys_to_sum = [
        "disk_reads",
        "disk_writes",
        "lnet_rx",
        "lnet_tx",
        "vnet_rx",
        "vnet_tx",
    ]

    aggregated = {key: 0 for key in keys_to_sum}
    total_cpu = 0
    count = 0

    for entry in response.get("data", []):
        stat = entry.get("stat", {})
        for key in keys_to_sum:
            aggregated[key] += stat.get(key, 0)
        # Для CPU считаем среднее значение
        total_cpu += stat.get("cpu", 0)
        count += 1

    aggregated["cpu"] = total_cpu / count if count else 0
    # Конвертация трафика из байт в гигабайты (1 ГБ = 10^9 байт)
    for key in ["lnet_rx", "lnet_tx", "vnet_rx", "vnet_tx"]:
        aggregated[key] /= 1e9

    return aggregated


@router.callback_query(F.data == "get_servers_info")
async def get_servers_info(callback: CallbackQuery):
    await callback.message.edit_text("Получение информации по серверам...")
    now = datetime.now()
    start = now - timedelta(days=30)
    servers_lst = await vdsina_processor.get_servers()
    # print(json.dumps(servers_lst, indent=4, ensure_ascii=False))

    data = {}
    for server in servers_lst["data"]:
        # print(server['id'])
        info = await vdsina_processor.get_server_statistics(server["id"])
        aggregated_stat = await aggregate_statistics(info)
        data[server["id"]] = aggregated_stat

    info = await make_servers_info_text(data)
    await callback.message.edit_text(
        text=info, reply_markup=get_back_admin_panel_keyboard()
    )


@router.callback_query(
    StateFilter(AdminAccess.admin_choosing_vpn_protocol_type),
    F.data.in_(["VPNtype_VLESS", "VPNtype_Outline"]),
)
async def make_key_for_admin(callback: CallbackQuery, state: FSMContext):
    try:
        match callback.data.split("_")[1].lower():
            case "outline":
                protocol_type = "Outline"
                key, server_id = await async_outline_processor.create_vpn_key()
            case "vless":
                protocol_type = "VLESS"
                key, server_id = await vless_processor.create_vpn_key()

        logger.info(f"Key created: {key} for user {callback.from_user.id}")

        await callback.message.edit_text(
            get_your_key_string(key, f"Ваш ключ «{key.name}»"),
            parse_mode="Markdown",
            reply_markup=get_back_admin_panel_keyboard(),
        )

        period = "12"
        db_processor.update_database_with_key(
            callback.from_user.id, key, period, server_id, protocol_type
        )

        # Отправка инструкций по установке
        await state.update_data(key_access_url=key.access_url)
    except Exception as e:
        logger.error(f"Произошла ошибка: {e}")
        await callback.answer(
            "Произошла ошибка при создании ключа. Пожалуйста, свяжитесь с поддержкой."
        )
        await state.clear()


@router.callback_query(
    F.data == "back_to_admin_panel",
    StateFilter(
        AdminAccess.correct_password, AdminAccess.admin_choosing_vpn_protocol_type
    ),
)
async def admin_panel(callback: CallbackQuery):
    await callback.message.edit_text(
        "👑 Вы вернулись в админ-панель", reply_markup=get_admin_keyboard()
    )
