from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.utils.get_processor import get_processor
from bot.utils.send_message import send_key_to_user_with_back_button
from bot.lexicon.lexicon import get_day_by_number
from bot.fsm.states import ManageKeys
from bot.initialization.db_processor_init import db_processor, session
from bot.initialization.async_outline_processor_init import async_outline_processor
from bot.initialization.vless_processor_init import vless_processor
from bot.keyboards.keyboards import (
    get_back_button_to_key_params,
    get_confirmation_keyboard,
    get_key_action_keyboard,
)


from logger.logging_config import setup_logger

router = Router()
logger = setup_logger()


@router.callback_query(F.data == "to_key_params")
@router.callback_query(
    StateFilter(ManageKeys.get_key_params), ~F.data.in_(["back_to_main_menu", "none"])
)
async def choosing_key_handler(callback: CallbackQuery, state: FSMContext):
    # Проверяем, начинается ли callback.data с "key_"
    if callback.data.startswith("key_"):
        # Извлекаем ID ключа из callback.data
        selected_key_id = callback.data.split("_")[1]
        # Сохраняем ID ключа в состоянии
        await state.update_data(selected_key_id=selected_key_id)
    else:
        # Если callback.data не содержит новый ID ключа, получаем его из состояния
        data = await state.get_data()
        selected_key_id = data.get("selected_key_id")

    # Проверка на случай, если selected_key_id всё ещё пустой
    if not selected_key_id:
        await callback.message.answer("ID ключа не найден.")
        return

    if not selected_key_id:
        await callback.message.answer(
            "Ключ не выбран. Пожалуйста, вернитесь назад и выберите ключ."
        )
        return

    # Получаем информацию о ключе из базы данных
    key = db_processor.get_key_by_id(selected_key_id)

    if not key:
        # await callback.message.answer("Ключ не найден.")
        return

    await callback.message.edit_text(
        f"Выберите действие для ключа: «{key.name}»",
        reply_markup=get_key_action_keyboard(key.key_id),
    )
    #
    # data = await state.get_data()
    # if data.get("key_info") is None:
    #     processor = await get_processor(key.protocol_type)
    #     key_info = await processor.get_key_info(key.key_id, server_id=key.server_id)
    #     logger.info(f"Key info: {key_info}")
    #
    #     # заносим всю инфу о ключе в дату, чтобы оперативно доставать её в других обработчиках
    #     await state.update_data(key_info=key_info)

    await state.set_state(ManageKeys.choose_key_action)


@router.callback_query(
    StateFilter(ManageKeys.choose_key_action), F.data.startswith("traffic")
)
async def show_traffic_handler(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    key_info = data.get("key_info")
    if key_info is None:
        key = db_processor.get_key_by_id(data.get("selected_key_id"))
        processor = await get_processor(key.protocol_type)
        key_info = await processor.get_key_info(key.key_id, server_id=key.server_id)
        logger.info(f"Key info: {key_info}")
        # заносим всю инфу о ключе в дату, чтобы оперативно доставать её в других обработчиках
        await state.update_data(key_info=key_info)

    used_bytes = 0

    if key_info.used_bytes is not None:
        used_bytes = key_info.used_bytes
    total_traffic = used_bytes / (1024**3)

    response = f"""
    Суммарный трафик: {total_traffic:.2f} Гб
    """
    await callback.message.edit_text(
        response, reply_markup=get_back_button_to_key_params()
    )


# дата окончания активации
@router.callback_query(
    StateFilter(ManageKeys.choose_key_action), F.data.startswith("expiration")
)
async def show_expiration_handler(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    key = db_processor.get_key_by_id(data["selected_key_id"])

    expiration_date = key.expiration_date
    if expiration_date:
        remaining_days = (expiration_date - datetime.now() + timedelta(days=1)).days
    else:
        remaining_days = None

    days = get_day_by_number(remaining_days)
    if remaining_days is not None:
        response = f"Действует до: {expiration_date.strftime('%d.%m.%Y')}\nДо окончания: {remaining_days} {days}"
    else:
        response = "Дата окончания не установлена."

    await callback.message.edit_text(
        response, reply_markup=get_back_button_to_key_params()
    )
    callback.answer()


@router.callback_query(
    StateFilter(ManageKeys.choose_key_action), F.data.startswith("rename")
)
async def ask_new_name_handler(callback: CallbackQuery, state: FSMContext):
    # Запрашиваем у пользователя новое имя для ключа
    await callback.message.edit_text("Введите новое имя для ключа:")
    # Переходим к следующему состоянию
    await state.set_state(ManageKeys.wait_for_new_name)


@router.message(StateFilter(ManageKeys.wait_for_new_name))
async def receive_new_name_handler(message: Message, state: FSMContext):
    new_name = message.text.strip()  # Получаем введенное имя

    # Проверяем, что имя не пустое
    if not new_name:
        await message.answer("Имя не может быть пустым. Пожалуйста, введите новое имя.")
        return

    # Сохраняем новое имя в состояние
    await state.update_data(new_name=new_name)

    # Запрашиваем подтверждение переименования
    await message.answer(
        f"Вы хотите переименовать ключ в «{new_name}»? Подтвердите действие.",
        reply_markup=get_confirmation_keyboard(),
    )

    # Переходим к состоянию подтверждения
    await state.set_state(ManageKeys.confirm_rename)


@router.callback_query(
    StateFilter(ManageKeys.confirm_rename), F.data == "confirm_rename"
)
async def confirm_rename_handler(callback: CallbackQuery, state: FSMContext):
    # Получаем данные из состояния
    data = await state.get_data()
    key_id = data["selected_key_id"]
    new_name = data["new_name"]

    # Получаем информацию о ключе из базы данных
    db_processor.rename_key(key_id, new_name)
    key = db_processor.get_key_by_id(key_id)

    # Переименовываем ключ через OutlineProcessor (если нужно)
    if key.protocol_type == "Outline":
        await async_outline_processor.rename_key(
            key.key_id, new_name, server_id=key.server_id
        )
    else:
        vless_processor.rename_key(key_id=key.key_id, new_key_name=new_name)
    # Отправляем сообщение пользователю
    await callback.message.edit_text(
        f"Ключ переименован в: {new_name}", reply_markup=get_back_button_to_key_params()
    )


@router.callback_query(
    StateFilter(ManageKeys.confirm_rename), F.data == "cancel_rename"
)
async def cancel_rename_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        "Переименование отменено.", reply_markup=get_back_button_to_key_params()
    )


@router.callback_query(
    StateFilter(ManageKeys.choose_key_action), F.data.startswith("access_url")
)
async def show_key_url_handler(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    key_info = data.get("key_info")
    if key_info is None:
        key = db_processor.get_key_by_id(data.get("selected_key_id"))
        processor = await get_processor(key.protocol_type)
        key_info = await processor.get_key_info(key.key_id, server_id=key.server_id)
        logger.info(f"Key info: {key_info}")
        # заносим всю инфу о ключе в дату, чтобы оперативно доставать её в других обработчиках
        await state.update_data(key_info=key_info)

    # Отправляем ключ пользователю
    await send_key_to_user_with_back_button(
        callback.message, key_info, f"Ваш ключ «{key_info.name}»"
    )
