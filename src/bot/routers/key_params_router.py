from aiogram.types import CallbackQuery, Message
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from bot.fsm.states import ManageKeys
from bot.initialization.db_processor_init import db_processor
from bot.initialization.outline_processor_init import outline_processor
from bot.keyboards.keyboards import (
    get_key_action_keyboard,
    get_confirmation_keyboard,
    get_back_button,
)
from bot.utils.send_message import send_key_to_user

from database.db_processor import DbProcessor
from logger.logging_config import setup_logger

from datetime import datetime

router = Router()
logger = setup_logger()


@router.callback_query(
    StateFilter(ManageKeys.get_key_params), ~F.data.in_(["back_to_main_menu"])
)
async def choosing_key_handler(callback: CallbackQuery, state: FSMContext):
    selected_key_id = callback.data.split("_")[1]  # Извлекаем ID ключа
    key_info = outline_processor.get_key_info(selected_key_id)

    # Сохраняем ID ключа в состоянии
    await state.update_data(selected_key_id=selected_key_id)

    # Теперь можем работать с выбранным ключом
    await callback.message.answer(f"Вы выбрали ключ: {key_info.name}")

    if not selected_key_id:
        await callback.message.answer(
            "Ключ не выбран. Пожалуйста, вернитесь назад и выберите ключ."
        )
        return

    # Получаем информацию о ключе из базы данных
    session = db_processor.get_session()
    key = session.query(DbProcessor.Key).filter_by(key_id=selected_key_id).first()

    if not key:
        await callback.message.answer("Ключ не найден.")
        return

    await callback.message.answer(
        "Выберите действие для ключа:", reply_markup=get_key_action_keyboard(key_info)
    )
    await state.set_state(ManageKeys.choose_key_action)


@router.callback_query(
    StateFilter(ManageKeys.choose_key_action), F.data.startswith("traffic")
)
async def show_traffic_handler(callback: CallbackQuery, state: FSMContext):
    key_id = callback.data.split("_")[1]  # Извлекаем ID ключа из callback_data

    # Получаем информацию о ключе из базы данных
    session = db_processor.get_session()
    key = session.query(DbProcessor.Key).filter_by(key_id=key_id).first()

    if not key:
        await callback.message.answer("Ключ не найден.")
        return

    # Логика вычисления трафика и среднего потребления

    key_info = outline_processor.get_key_info(key_id)
    used_bytes = 0
    if key_info.used_bytes is not None:
        used_bytes = key_info.used_bytes
    total_traffic = used_bytes / (1024**2)

    # надо как-то считать
    avg_daily_usage = 1  # Сюда ваш расчет среднего использования в сутки
    avg_day_usage = 1  # Среднее дневное использование
    avg_night_usage = 0.5  # Среднее ночное использование

    response = f"""
    Суммарный трафик: {total_traffic} Гб
    Среднее использование в сутки: {avg_daily_usage} Гб/сут
    Среднее использование за день/ночь: {avg_day_usage} Гб / {avg_night_usage} Гб
    """

    await callback.message.answer(response, reply_markup=get_back_button())


# Пример для другого действия, например, дата окончания активации
@router.callback_query(
    StateFilter(ManageKeys.choose_key_action), F.data.startswith("expiration")
)
async def show_expiration_handler(callback: CallbackQuery, state: FSMContext):
    key_id = callback.data.split("_")[1]  # Извлекаем ID ключа

    # Получаем информацию о ключе из базы данных
    session = db_processor.get_session()
    key = session.query(DbProcessor.Key).filter_by(key_id=key_id).first()

    if not key:
        await callback.message.answer("Ключ не найден.")
        return

    # Логика для вычисления даты окончания активации
    expiration_date = key.expiration_date
    if expiration_date:
        # Вычисляем количество оставшихся дней
        remaining_days = (expiration_date - datetime.now()).days
    else:
        remaining_days = None

    if remaining_days is not None:
        response = f"""
            Действует до: {expiration_date.strftime('%d.%m.%Y')}
            До окончания: {remaining_days} дней
            """
    else:
        response = "Дата окончания не установлена."

    await callback.message.answer(response, reply_markup=get_back_button())


# Пример для действия "Продлить ключ"
@router.callback_query(
    StateFilter(ManageKeys.choose_key_action), F.data.startswith("extend")
)
async def extend_key_handler(callback: CallbackQuery, state: FSMContext):
    key_id = callback.data.split("_")[1]  # Извлекаем ID ключа

    # Логика продления ключа (например, обновление даты окончания)
    session = db_processor.get_session()
    key = session.query(DbProcessor.Key).filter_by(key_id=key_id).first()

    if not key:
        await callback.message.answer("Ключ не найден.")
        return

    # Пример логики продления
    # Обновить дату окончания ключа и сохранить
    # key.expiration_date = new_expiration_date
    session.commit()

    await callback.message.answer(
        "Ключ успешно продлен!", reply_markup=get_back_button()
    )


@router.callback_query(
    StateFilter(ManageKeys.choose_key_action), F.data.startswith("rename")
)
async def ask_new_name_handler(callback: CallbackQuery, state: FSMContext):
    key_id = callback.data.split("_")[1]  # Извлекаем ID ключа

    # Сохраняем key_id в состоянии FSMContext
    await state.update_data(selected_key_id=key_id)

    # Запрашиваем у пользователя новое имя для ключа
    await callback.message.answer("Введите новое имя для ключа:")

    # Переходим к следующему состоянию
    await state.set_state(ManageKeys.wait_for_new_name)


@router.message(StateFilter(ManageKeys.wait_for_new_name))
async def receive_new_name_handler(message: Message, state: FSMContext):
    new_name = message.text.strip()  # Получаем введенное имя

    # Проверяем, что имя не пустое
    if not new_name:
        await message.answer("Имя не может быть пустым. Пожалуйста, введите новое имя.")
        return

    # Получаем ID ключа из состояния
    user_data = await state.get_data()
    key_id = user_data["selected_key_id"]

    # Сохраняем новое имя в состояние
    await state.update_data(new_name=new_name)

    # Запрашиваем подтверждение переименования
    await message.answer(
        f"Вы хотите переименовать ключ в '{new_name}'? Подтвердите действие.",
        reply_markup=get_confirmation_keyboard(),
    )

    # Переходим к состоянию подтверждения
    await state.set_state(ManageKeys.confirm_rename)


@router.callback_query(
    StateFilter(ManageKeys.confirm_rename), F.data == "confirm_rename"
)
async def confirm_rename_handler(callback: CallbackQuery, state: FSMContext):
    # Получаем данные из состояния
    user_data = await state.get_data()
    key_id = user_data["selected_key_id"]
    new_name = user_data["new_name"]

    # Получаем информацию о ключе из базы данных
    session = db_processor.get_session()
    key = session.query(DbProcessor.Key).filter_by(key_id=key_id).first()

    if not key:
        await callback.message.answer("Ключ не найден.")
        return

    # Переименовываем ключ в базе данных
    key.name = new_name
    session.commit()

    # Переименовываем ключ через OutlineProcessor (если нужно)
    outline_processor.rename_key(key_id=key.key_id, new_key_name=new_name)

    # Отправляем сообщение пользователю
    await callback.message.answer(
        f"Ключ переименован в: {new_name}", reply_markup=get_back_button()
    )


@router.callback_query(
    StateFilter(ManageKeys.confirm_rename), F.data == "cancel_rename"
)
async def cancel_rename_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Переименование отменено.", reply_markup=get_back_button()
    )


@router.callback_query(
    StateFilter(ManageKeys.choose_key_action), F.data.startswith("access_url")
)
async def show_key_url_handler(callback: CallbackQuery, state: FSMContext):
    key_id = callback.data.split("_")[2]  # Извлекаем ID ключа

    # Получаем информацию о ключе из базы данных
    session = db_processor.get_session()
    key = session.query(DbProcessor.Key).filter_by(key_id=key_id).first()

    key_info = outline_processor.get_key_info(key_id)

    if not key:
        await callback.message.answer("Ключ не найден.")
        return

    # Отправляем ключ пользователю
    await send_key_to_user(callback.message, key_info, f"Ваш ключ «{key_info.name}»")
