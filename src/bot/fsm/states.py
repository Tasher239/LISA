from aiogram.fsm.state import State, StatesGroup


class MainMenu(StatesGroup):
    waiting_for_action = State()
    about_us = State()


class GetKey(StatesGroup):
    choosing_vpn_protocol_type = State()
    choosing_period = State()
    waiting_for_payment = State()
    sending_key = State()
    buy_key = State()
    waiting_for_extension_payment = State()
    choice_extension_period = State()


class ManageKeys(StatesGroup):
    key_management_no_key = State()
    choosing_key = State()
    choosing_action = State()
    rename_key = State()
    choose_trial_key = State()
    get_key_params = State()
    choose_key_action = State()
    wait_for_new_name = State()
    confirm_rename = State()
    key_management_pressed = State()
    no_active_keys = State()


class SubscriptionExtension(StatesGroup):
    extension = State()
