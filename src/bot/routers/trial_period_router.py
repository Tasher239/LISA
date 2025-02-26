from datetime import datetime, timedelta

from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery
from aiogram import F, Router

from database.models import VpnKey
from database.models import User
from initialization.async_outline_processor_init import async_outline_processor
from initialization.vless_processor_init import vless_processor
from initialization.db_processor_init import db_processor
from bot.utils.send_message import send_key_to_user
from bot.fsm.states import GetKey, ManageKeys
from bot.keyboards.keyboards import (
    get_already_have_trial_key_keyboard,
    get_choice_vpn_type_keyboard_for_no_key,
)


from logger.logging_config import setup_logger

router = Router()
logger = setup_logger()


@router.callback_query(
    StateFilter(ManageKeys.no_active_keys), F.data == "get_trial_period"
)
async def trial_key_protocol_type_choice(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Выберите тип подключения:",
        reply_markup=get_choice_vpn_type_keyboard_for_no_key(),
    )


@router.callback_query(
    StateFilter(ManageKeys.no_active_keys),
    F.data.in_(["VPNtype_Outline", "VPNtype_VLESS"]),
)
@router.callback_query(StateFilter(GetKey.buy_key), F.data == "trial_period")
async def handle_trial_key_choice(callback: CallbackQuery, state: FSMContext):
    """Если пользователь выбрал использовать пробный ключ
    Проверяем, что пользователь не использовал пробный период ранее
    Если использовал возвращаем сообщение, что пробный период уже заюзан
    И делаем 2 кнопки - назад и купить ключ"""

    cur_state = await state.get_state()
    match cur_state:
        case GetKey.buy_key:
            data = await state.get_data()
            vpn_type = data.get("vpn_type")
        case ManageKeys.no_active_keys:
            vpn_type = callback.data.split("_")[1]

    user_id = callback.from_user.id
    user_id_str = str(user_id)
    session = db_processor.get_session()

    user = session.query(User).filter_by(user_telegram_id=user_id_str).first()

    if not user:
        user = User(
            user_telegram_id=user_id_str,
            subscription_status="active",  # тут поменять + добавить информацию о конце периода для ключа
            use_trial_period=False,
        )
        session.add(user)
        session.commit()

    if not user.use_trial_period:
        # обновляем статус использования пробного периода
        # генерируем и высылаем ключ
        user.use_trial_period = True
        session.commit()

        # processor = await get_processor(vpn_type)

        match vpn_type.lower():
            case "outline":
                processor = async_outline_processor
                key, server_id = await processor.create_vpn_key()
            case "vless":
                processor = vless_processor
                key, server_id = await processor.create_vpn_key()

        start_date = datetime.now()
        await state.update_data(key_access_url=key.access_url)
        expiration_date = start_date + timedelta(days=2)
        new_key = VpnKey(
            key_id=key.key_id,
            name=key.name,
            user_telegram_id=user_id_str,
            expiration_date=expiration_date,
            start_date=start_date,
            protocol_type=vpn_type,
            server_id=server_id,
        )
        session.add(new_key)
        session.commit()

        text = f"Ваш пробный ключ «{key.name}» готов к использованию. Срок действия - 2 дня."
        await send_key_to_user(callback.message, key, text)
    else:
        current_state = await state.get_state()
        await callback.message.edit_text(
            "Вы уже использовали пробный период. "
            "Вы можете купить ключ или вернуться в главное меню",
            reply_markup=get_already_have_trial_key_keyboard(current_state),
        )
    await state.set_state(GetKey.get_trial_key)
