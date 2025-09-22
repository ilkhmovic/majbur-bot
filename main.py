import os
import json
import asyncio
import logging
import re
import subprocess
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.enums import ContentType
from aiogram.filters import Command, StateFilter
from aiogram.exceptions import TelegramNetworkError, TelegramAPIError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# Handlerlar va states importi
from handlers import (
    start_command,
    handle_text_messages,
    handle_callback_queries,
    process_screenshot,
    admin_approve_payment,
    process_bot_token,
    process_bot_username,
    process_deposit_amount,
    cancel_command,
    admin_command, # <-- Yangi import
    process_new_channel_id, # <-- Yangi import
    check_subscription 
)
from states import BotCreationStates,AdminStates

# Loggingni sozlash
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Sizning asosiy bot tokeningiz va boshqa konfiguratsiyalar
API_TOKEN = '8343012605:AAFUEX_xP3PuutUq_AV9nImq4VxqFXwu9tQ'
ADMIN_ID = 7798312047

# Storage, Bot va Dispatcher obyektlarini yaratish
storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=storage)

bot.dp = dp

# Handlerlarga kerakli o'zgaruvchilarni Dependency Injection orqali uzatish
dp["ADMIN_ID"] = ADMIN_ID

def ensure_file(filename, default_data):
    try:
        if not os.path.exists(filename):
            with open(filename, "w", encoding='utf-8') as f:
                json.dump(default_data, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ {filename} fayli yaratildi.")
        else:
            logger.info(f"✅ {filename} fayli mavjud.")
    except Exception as e:
        logger.error(f"❌ {filename} faylini yaratishda xatolik: {e}")

def load_json(filename):
    try:
        with open(filename, "r", encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning(f"Fayl topilmadi yoki bo'sh: {filename}. Bo'sh ro'yxat qaytarildi.")
        return []

def start_new_bot_process(bot_token, username):
    try:
        subprocess.Popen(["python", "new_bot.py", bot_token, username])
        logger.info(f"Yangi bot jarayoni ishga tushirildi: @{username}")
    except Exception as e:
        logger.error(f"❌ Botni ishga tushirishda xatolik: {e}")

ensure_file("multibot_data.json", [])
ensure_file("users.json", {})
ensure_file("bot_creation_times.json", {})

# --- Handlerni ro'yxatdan o'tkazish (MUHIM: Tartibga e'tibor bering) ---
dp.message.register(cancel_command, Command("cancel"), StateFilter("*"))


# 1. FSM holatlariga bog'liq handlerlar har doim birinchi bo'lishi kerak.
dp.message.register(process_bot_token, Command("token"), StateFilter(BotCreationStates.waiting_for_token))
dp.message.register(process_deposit_amount, StateFilter(BotCreationStates.waiting_for_deposit_amount))
dp.message.register(process_screenshot, F.photo, StateFilter(BotCreationStates.waiting_for_screenshot))
dp.message.register(process_bot_username, StateFilter(BotCreationStates.waiting_for_username))

# 2. Keyin buyruqlar va callbacklar.
dp.message.register(start_command, Command("start"))
dp.callback_query.register(admin_approve_payment, F.data.startswith(("admin_approve_deposit", "admin_approve")))
dp.callback_query.register(handle_callback_queries)

dp.message.register(admin_command, Command("admin"), F.from_user.id == ADMIN_ID)
dp.message.register(process_new_channel_id, StateFilter(AdminStates.waiting_for_channel_id))
dp.callback_query.register(check_subscription, F.data == "check_subscription")

# 3. Va eng oxirida umumiy matn handlerlari.
dp.message.register(handle_text_messages, F.text)

async def main():
    logger.info("🚀 Asosiy bot ishga tushmoqda...")
    multibot_data = load_json("multibot_data.json")
    for bot_info in multibot_data:
        start_new_bot_process(bot_info["bot_token"], bot_info.get("username", "no_username"))

    try:
        await dp.start_polling(bot, skip_updates=True)
    except KeyboardInterrupt:
        logger.info("Bot to'xtatildi (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Botda kutilmagan xatolik: {e}")
        await asyncio.sleep(5)
        logger.info("🔄 Bot qaytadan ishga tushirilmoqda...")

if __name__ == '__main__':
    asyncio.run(main())