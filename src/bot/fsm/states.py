from aiogram.fsm.state import default_state, State, StatesGroup


class MainMenu(StatesGroup):
    waiting_for_action = State()

class GetKey(StatesGroup):
    choosing_period = State()
    waiting_for_payment = State()
    sending_key = State()

class ManageKeys(StatesGroup):
    choosing_key = State()
    choosing_action = State()
    rename_key = State()
