from aiogram.fsm.state import default_state, State, StatesGroup


class MainMenu(StatesGroup):
    waiting_for_action = State()


class GetKey(StatesGroup):
    choosing_period = State()
    waiting_for_payment = State()
    sending_key = State()
    prodlenie = State()


class ManageKeys(StatesGroup):
    choosing_key = State()
    choosing_action = State()
    rename_key = State()
    choose_trial_key = State()
    get_key_params = State()
    choose_key_action = State()
    wait_for_new_name = State()
    confirm_rename = State()


class Subscription_prodl(StatesGroup):
    reminder = State()
    expired = State()
