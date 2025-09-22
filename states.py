# states.py

from aiogram.fsm.state import State, StatesGroup

class BotCreationStates(StatesGroup):
    waiting_for_payment_confirmation = State()
    waiting_for_screenshot = State()
    waiting_for_token = State()
    waiting_for_username = State()
    waiting_for_admin_approval = State()
    waiting_for_admin_password = State()  
    waiting_for_deposit_amount = State()
    waiting_for_channel_id = State()

class AdminStates(StatesGroup):
    waiting_for_admin_id = State()
    waiting_for_channel_id = State() # Yangi qator