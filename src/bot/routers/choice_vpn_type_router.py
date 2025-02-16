from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.filters import StateFilter
from aiogram import F, Router

from bot.keyboards.keyboards import get_choice_vpn_type_keyboard
from bot.fsm.states import GetKey, ManageKeys, AdminAccess

from logger.logging_config import setup_logger

router = Router()
logger = setup_logger()


@router.callback_query(
    StateFilter(ManageKeys.no_active_keys), F.data.in_(["get_keys_pressed"])
)
@router.callback_query(
    F.data.in_(["choice_vpn_type", "back_to_choice_vpn_type", "admin_choice_vpn_type"])
)
async def choice_vpn_type(callback: CallbackQuery, state: FSMContext):
    if callback.data == "admin_choice_vpn_type":
        await state.set_state(AdminAccess.admin_choosing_vpn_protocol_type)
    else:
        await state.set_state(GetKey.choosing_vpn_protocol_type)
    current_state = await state.get_state()
    await callback.message.edit_text(
        "Выберите тип подключения:",
        reply_markup=get_choice_vpn_type_keyboard(current_state),
    )
