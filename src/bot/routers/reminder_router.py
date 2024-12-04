from aiogram.types import Message, CallbackQuery
from aiogram import F, Router
from aiogram.fsm.context import FSMContext

from bot.keyboards.keyboards import get_prodlenie_keyboard
from bot.fsm.states import GetKey

from logger.logging_config import setup_logger

router = Router()
router.message.filter(F.data == "extend_now")
logger = setup_logger()


@router.message()
async def prodlenie(message: Message, state: FSMContext):
    if F.data == "extend_now":
        await message.answer(
            text="Выберите период продления:",
            reply_markup=get_prodlenie_keyboard(),
            state=GetKey.prodlenie,
        )
