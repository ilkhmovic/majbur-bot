import os
import json
import asyncio
import subprocess
import logging
from aiogram import types, F, Bot, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.storage.base import StorageKey
from states import BotCreationStates,AdminStates
from keyboards import (
    main_menu,
    manage_bot_menu,
    i_agree_kb,
    paid_kb,
    cabinet_kb,
    payment_options_kb,
    card_payment_kb,
    deposit_card_kb,
    bot_settings_kb,
    bot_payment_options_kb,
    admin_bot_list_kb,
    admin_channels_kb,
    admin_main_kb
)
from datetime import datetime
import re

# Loggingni sozlash
logger = logging.getLogger(__name__)

# --- Yordamchi funksiyalar ---
def get_user_data(user_id):
    """Foydalanuvchi ma'lumotlarini JSON fayldan o'qiydi yoki yangi foydalanuvchi yaratadi."""
    try:
        with open("users.json", "r", encoding='utf-8') as f:
            users_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        users_data = {}

    user_data = users_data.get(str(user_id), {})
    if not user_data:
        user_data = {"balance": 0, "status": "Oddiy", "donations": 0}
        users_data[str(user_id)] = user_data
        with open("users.json", "w", encoding='utf-8') as f:
            json.dump(users_data, f, indent=2, ensure_ascii=False)
    return user_data

def update_user_data(user_id, new_data):
    """Foydalanuvchi ma'lumotlarini JSON faylga yangilaydi."""
    try:
        with open("users.json", "r", encoding='utf-8') as f:
            users_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        users_data = {}

    users_data[str(user_id)] = new_data
    with open("users.json", "w", encoding='utf-8') as f:
        json.dump(users_data, f, indent=2, ensure_ascii=False)

def get_multibot_data():
    try:
        with open("multibot_data.json", "r", encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def update_multibot_data(new_data):
    try:
        with open("multibot_data.json", "w", encoding='utf-8') as f:
            json.dump(new_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"❌ multibot_data.jsonni yangilashda xatolik: {e}")

def get_bot_creation_time(bot_username):
    try:
        with open("bot_creation_times.json", "r", encoding='utf-8') as f:
            bot_times = json.load(f)
            return bot_times.get(bot_username.replace('@', ''), "Noma'lum vaqt")
    except (FileNotFoundError, json.JSONDecodeError):
        return "Noma'lum vaqt"

def update_bot_creation_time(bot_username, timestamp):
    try:
        with open("bot_creation_times.json", "r", encoding='utf-8') as f:
            bot_times = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        bot_times = {}
    bot_times[bot_username.replace('@', '')] = timestamp
    with open("bot_creation_times.json", "w", encoding='utf-8') as f:
        json.dump(bot_times, f, indent=2, ensure_ascii=False)
def load_json(filename, default_value={}):
    try:
        if not os.path.exists(filename):
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(default_value, f, indent=4, ensure_ascii=False)
            return default_value
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Faylni yuklashda xatolik: {filename} - {e}. Yangi fayl yaratilmoqda.")
        return default_value

def save_json(filename, data):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Faylni saqlashda xatolik: {filename} - {e}")

def get_admin_channels():
    # Admin kanallarini saqlash uchun yangi fayl
    return load_json("admin_channels.json", default_value=[])

def save_admin_channels(data):
    save_json("admin_channels.json", data)

# --- Handler funksiyalar ---
async def start_command(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    
    channels = get_admin_channels()
    if channels:
        unsubscribed_channels = []
        for channel_id in channels:
            try:
                member = await bot.get_chat_member(chat_id=channel_id, user_id=message.from_user.id)
                if member.status in ["left", "kicked"]:
                    unsubscribed_channels.append(channel_id)
            except Exception as e:
                logger.error(f"❌ Kanal ({channel_id}) a'zoligini tekshirishda xatolik: {e}")
                unsubscribed_channels.append(channel_id)

        if unsubscribed_channels:
            text = "Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:\n\n"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[])
            for channel_id in unsubscribed_channels:
                try:
                    chat = await bot.get_chat(channel_id)
                    invite_link = chat.invite_link
                    if not invite_link:
                        invite_link = await chat.create_invite_link()
                    keyboard.inline_keyboard.append([InlineKeyboardButton(text=f"@{chat.username}", url=invite_link)])
                except Exception as e:
                    logger.error(f"❌ Kanal ma'lumotlarini olishda xatolik: {e}")
                    keyboard.inline_keyboard.append([InlineKeyboardButton(text=f"Kanal {channel_id}", url=f"https://t.me/c/{str(channel_id)[4:]}")])

            keyboard.inline_keyboard.append([InlineKeyboardButton(text="✅ Obunani tasdiqlash", callback_data="check_subscription")])
            
            await message.answer(text, reply_markup=keyboard)
            return

    await message.answer(
        "Assalomu alaykum! Bosh menyuga xush kelibsiz.",
        reply_markup=main_menu
    )


    

async def handle_text_messages(message: types.Message, state: FSMContext,bot:Bot):
    current_state = await state.get_state()
    if current_state:
        if current_state == BotCreationStates.waiting_for_deposit_amount.state:
            await message.answer("⏳ Hisobni to‘ldirish jarayoni yakunlanmagan. Iltimos, miqdor kiriting yoki `/cancel` bilan bekor qiling.")
        elif current_state == BotCreationStates.waiting_for_token.state:
            await message.answer("⏳ Bot tokenini kuting yoki `/cancel` bilan bekor qiling.")
    if message.text == "🆕 Bot yaratish":
        await message.answer(
            "Bot ochish 30 000 soʻm, oylik toʻlov 20 000 soʻm. Siz rozi bo'lsangiz, davom etamiz.",
            reply_markup=i_agree_kb
        )
    elif message.text == "⚙️ Bot sozlash":
        user_id = message.from_user.id
        multibot_data = get_multibot_data()
        user_bots = [bot_info for bot_info in multibot_data if bot_info.get("owner_id") == user_id]
        
        if not user_bots:
            await message.answer("Sizda hozircha hech qanday bot yo'q.")
            return

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"@{bot_info['username']}", callback_data=f"select_bot_{i}")]
            for i, bot_info in enumerate(user_bots)
        ])
        await message.answer("Sizning botlaringiz:", reply_markup=keyboard)

    elif message.text == "🤖 Botlarni boshqarish":
        await message.answer(
            "Botlarni boshqarish bo'limiga xush kelibsiz.",
            reply_markup=manage_bot_menu
        )
    elif message.text == "👤 Kabinet":
        await state.clear()
        user_id = message.from_user.id
        user_data = get_user_data(user_id)
        balance = user_data.get("balance", 0)
        status = user_data.get("status", "Oddiy")
        donations = user_data.get("donations", 0)

        text = (
            f"🔎 UID: `{user_id}`\n"
            f"├─💵 Balansingiz: `{balance}` so'm\n"
            f"├─👑 Statusingiz: `{status}`\n"
            f"└─➕ Kiritgan pullaringiz: `{donations}` so'm"
        )
        await message.answer(text, reply_markup=cabinet_kb, parse_mode="Markdown")
    elif message.text == "➕ Hisobni to‘ldirish":
        await message.answer("Qancha miqdorda hisobni to'ldirmoqchisiz? (Yoki `/cancel` bilan bekor qiling)")
        await state.set_state(BotCreationStates.waiting_for_deposit_amount)
    
    elif message.text == "📖 Qo‘llanma":
        manual_text = (
            "**Bot qoʻllanmasi**\n"
            "Bu bot sizga shaxsiy botingizni yaratish va boshqarish imkonini beradi. "
            "Quyida botning asosiy funksiyalari haqida qisqacha maʼlumot berilgan:\n\n"
            "---"
            "\n**▶️ Bot yaratish:**\n"
            "Bot yaratish jarayoni toʻlovdan boshlanadi. **Bot yaratish** tugmasini bosganingizdan soʻng, xizmat uchun toʻlovni amalga oshirasiz. Toʻlov tasdiqlangach, botingizni sozlash uchun quyidagi amallarni bajarasiz:\n"
            "  •  **Tokenni yuborish:** BotFather orqali yaratilgan botingizning tokenini yuborasiz. Misol: `123456:ABC...`\n"
            "  •  **Username'ni yuborish:** Botingizning username'ini (misol: `my_new_bot`) yuborasiz.\n"
            "Bu maʼlumotlar qabul qilingandan soʻng, botingiz tizimda ishga tushiriladi.\n\n"
            "---"
            "\n**▶️ Hisobni toʻldirish:**\n"
            "Bu boʻlim orqali asosiy botdagi shaxsiy balansingizni toʻldirishingiz mumkin. Toʻldirilgan balans kelajakda **premium bot** yoki boshqa pullik xususiyatlar uchun ishlatiladi.\n"
            "  •  Toʻlovni amalga oshirib, skrinshotni yuborasiz.\n"
            "  •  Admin tasdiqlagach, mablagʻingiz balansingizga qoʻshiladi.\n\n"
            "---"
            "\n**▶️ Kabinet:**\n"
            "Bu sizning shaxsiy maʼlumotlaringiz joylashgan boʻlimdir. Bu yerda siz:\n"
            "  •  Balansingizni.\n"
            "  •  Toʻlovlar tarixingizni.\n"
            "  •  Premium maqomingizni koʻrishingiz mumkin.\n\n"
            "---"
            "\n**▶️ Yangi botni ishga tushirish va boshqarish:**\n"
            "Yangi bot yaralgach, u avtomatik ravishda ishga tushadi. Unga kirib `/start` buyrugʻini yuborsangiz, asosiy menyu chiqadi.\n"
            "  •  **Admin panel:** Botning admin paneliga kirish uchun **`/admin`** buyrugʻini yuboring. Bu buyruqni faqat bot egasi ishlata oladi.\n"
            "  •  **Kinolar qoʻshish:** Admin panelda **\"🎬 Kino qo'shish\"** tugmasini bosib, kinolar haqida maʼlumot kiritasiz. Format:\n"
            "     `Kino nomi | Kino haqida ma'lumot | Kino linki`\n"
            "     *Misol: `Titanik | 1912-yilda... | https://t.me/...`*\n"
            "  •  **Kanallar qoʻshish:** Admin panelda **\"📢 Kanal qo'shish\"** tugmasi orqali botdan foydalanishdan oldin obuna boʻlishi kerak boʻlgan kanallarning ID’sini qoʻshishingiz mumkin.\n"
        )
        await message.answer(manual_text, parse_mode="Markdown")
    elif message.text == "🆘 Yordam":
        admin_id = bot.dp["ADMIN_ID"] # Asosiy botdagi ADMIN_ID ni olamiz
        admin_link_button = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Admin bilan bog'lanish 👨🏻‍💻", url=f"tg://user?id={admin_id}")]
        ])
        
        await message.answer(
            "Yordam bo'limiga xush kelibsiz!\n\n"
            "Agar bot funksiyalari bo'yicha savollaringiz bo'lsa, "
            "**Qo‘llanma** bo'limidagi videolarni tomosha qiling.\n\n"
            "Agar botda xato yuz bergan bo'lsa yoki boshqa texnik muammo bo'lsa, "
            "quyidagi tugma orqali adminga murojaat qiling:",
            reply_markup=admin_link_button,
            parse_mode="Markdown"
        )
    elif message.text == "🔙 Ortga qaytish":
        await message.answer("Bosh menyuga qaytish.", reply_markup=main_menu)
    elif message.text == "📢 Kanal qo'shish":
        ADMIN_ID = bot.dp["ADMIN_ID"]
        if message.from_user.id != ADMIN_ID:
            await message.answer("Siz admin emassiz.")
            return
        await message.answer("Iltimos, qo'shmoqchi bo'lgan kanal ID'sini yuboring. \nMasalan: `-100123456789`")
        await state.set_state(AdminStates.waiting_for_channel_id)
    elif message.text == "❌ Tugmalarni yopish":
        ADMIN_ID = bot.dp["ADMIN_ID"]
        if message.from_user.id != ADMIN_ID:
            await message.answer("Siz admin emassiz.")
            return
        await message.answer("Admin paneli yopildi.", reply_markup=main_menu)
    else:
        await message.answer("Tushunarsiz buyruq. Iltimos, menyudan foydalaning.")
    

async def process_deposit_amount(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("✅ Hisobni to‘ldirish jarayoni bekor qilindi.", reply_markup=main_menu)
        return

    try:
        amount = int(message.text)
        if amount <= 0:
            await message.reply("Noto'g'ri miqdor. Iltimos, musbat son kiriting.")
            return

        await state.update_data(deposit_amount=amount)
        await message.answer(
            f"Siz {amount} so'm miqdorida hisobni to'ldirmoqchisiz.\n\n"
            f"To'lovni quyidagi karta raqamiga amalga oshiring:\n"
            f"Karta raqami: **6262 5700 9817 0949**\n"
            f"Qabul qiluvchi: **Xolikov Maxxammadyunus**\n\n"
            f"Toʻlovni amalga oshirgach, pastdagi tugmani bosing:",
            reply_markup=deposit_card_kb,
            parse_mode="Markdown"
        )
        await state.set_state(BotCreationStates.waiting_for_screenshot)
    except ValueError:
        await message.reply("Noto'g'ri format. Iltimos, faqat raqam kiriting yoki `/cancel` bilan bekor qiling.")

async def handle_callback_queries(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.from_user.id
    multibot_data = get_multibot_data()

    if callback.data == "create_new_bot":
        await callback.answer()
        await callback.message.answer(
            "Bot ochish 30 000 soʻm, oylik toʻlov 20 000 soʻm. Siz rozi bo'lsangiz, davom etamiz.",
            reply_markup=i_agree_kb
        )
    elif callback.data == "i_agree_to_pay":
        await callback.answer()
        await callback.message.answer(
            "Toʻlovni quyidagi karta raqamiga amalga oshiring:\n\n"
            "Karta raqami: **6262 5700 9817 0949**\n"
            "Qabul qiluvchi: **Xolikov Maxxammadyunus**\n\n"
            "Toʻlovni amalga oshirgach, pastdagi tugmani bosing:",
            reply_markup=paid_kb
        )
        await state.update_data(payment_type="bot_creation", amount=30000)
    elif callback.data == "i_paid":
        await callback.answer()
        await callback.message.answer("Iltimos, toʻlov chekining skrinshotini yuboring.")
        await state.set_state(BotCreationStates.waiting_for_screenshot)
    elif callback.data == "settings_bot":
        await callback.answer()
        user_bots = [bot for bot in multibot_data if bot.get("owner_id") == user_id]
        if not user_bots:
            await callback.message.answer("Sizda hozircha hech qanday bot yo'q.")
            return
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"@{bot['username']} (Yaratilgan: {get_bot_creation_time(bot['username'])})", callback_data=f"select_bot_{i}")]
            for i, bot in enumerate(user_bots)
        ])
        await callback.message.answer("Sizning botlaringiz:", reply_markup=keyboard)
    elif callback.data.startswith("select_bot_"):
        bot_index = int(callback.data.split("_")[2])
        user_bots = [bot for bot in multibot_data if bot.get("owner_id") == user_id]
        selected_bot = user_bots[bot_index]
        keyboard = bot_settings_kb(selected_bot['username'])
        await callback.message.edit_text(f"@{selected_bot['username']} sozlamalari:", reply_markup=keyboard)
    elif callback.data.startswith("change_token_"):
        bot_username = callback.data.split("_")[2]
        await callback.answer()
        await callback.message.answer(f"@{bot_username} uchun yangi bot tokenini kiriting. (Yoki `/cancel` bilan bekor qiling)")
        await state.update_data(bot_username=bot_username)
        await state.set_state(BotCreationStates.waiting_for_token)
    elif callback.data.startswith("change_username_"):
        bot_username = callback.data.split("_")[2]
        await callback.answer()
        await callback.message.answer(f"@{bot_username} uchun yangi bot username'ini kiriting. (Yoki `/cancel` bilan bekor qiling)")
        await state.update_data(bot_username=bot_username)
        await state.set_state(BotCreationStates.waiting_for_username)
    elif callback.data.startswith("pay_monthly_"):
        bot_username = callback.data.split("_")[2]
        keyboard = bot_payment_options_kb(bot_username)
        await callback.message.edit_text(f"@{bot_username} uchun oylik to'lov (20 000 so'm):", reply_markup=keyboard)
    elif callback.data == "pay_with_card_monthly":
        await callback.answer()
        await callback.message.answer(
            "💳 **Karta orqali to'lov**\n\n"
            "Toʻlovni quyidagi karta raqamiga amalga oshiring:\n"
            "Karta raqami: **6262 5700 9817 0949**\n"
            "Qabul qiluvchi: **Xolikov Maxxammadyunus**\n\n"
            "Toʻlovni amalga oshirgach, pastdagi tugmani bosing:",
            reply_markup=card_payment_kb
        )
        await state.update_data(payment_type="monthly", amount=20000)
        await state.set_state(BotCreationStates.waiting_for_screenshot)
    elif callback.data == "pay_with_balance_monthly":
        user_id = callback.from_user.id
        user_data = get_user_data(user_id)
        monthly_fee = 20000
        user_balance = user_data.get("balance", 0)
        if user_balance >= monthly_fee:
            user_data["balance"] -= monthly_fee
            update_user_data(user_id, user_data)
            await callback.answer("✅ Muvaffaqiyatli! Sizning hisobingizdan 20000 so'm yechildi.", show_alert=True)
            await callback.message.answer(f"🎉 Tabriklaymiz! Oylik to'lov amalga oshirildi.")
        else:
            await callback.answer("❌ Hisobingizda mablag' yetarli emas. Iltimos, hisobingizni to'ldiring.", show_alert=True)
            await callback.message.answer("Hisobingizni to'ldirish uchun menyudan 'Hisobni to‘ldirish' tugmasini bosing.")
    elif callback.data == "buy_premium":
        user_id = callback.from_user.id
        user_data = get_user_data(user_id)
        if user_data.get("status") == "Premium":
            await callback.answer("Siz allaqachon Premium obunachisiz.", show_alert=True)
            return
        await callback.answer()
        await callback.message.answer(
            "💎 **Premium xizmati**\n\n"
            "Xizmat narxi: **5000 so'm**\n\n"
            "To'lov turini tanlang:",
            reply_markup=payment_options_kb,
            parse_mode="Markdown"
        )
    elif callback.data == "pay_with_card":
        await callback.answer()
        await callback.message.answer(
            "💳 **Karta orqali to'lov**\n\n"
            "Toʻlovni quyidagi karta raqamiga amalga oshiring:\n"
            "Karta raqami: **6262 5700 9817 0949**\n"
            "Qabul qiluvchi: **Xolikov Maxxammadyunus**\n\n"
            "Toʻlovni amalga oshirgach, pastdagi tugmani bosing:",
            reply_markup=card_payment_kb,
            parse_mode="Markdown"
        )
        await state.update_data(payment_type="premium_card", amount=5000)
        await state.set_state(BotCreationStates.waiting_for_screenshot)
    elif callback.data == "pay_with_balance":
        user_id = callback.from_user.id
        user_data = get_user_data(user_id)
        premium_price = 5000
        user_balance = user_data.get("balance", 0)
        if user_balance >= premium_price:
            user_data["balance"] -= premium_price
            user_data["status"] = "Premium"
            update_user_data(user_id, user_data)
            await callback.answer("✅ Muvaffaqiyatli! Sizning hisobingizdan 5000 so'm yechildi. Siz endi Premium foydalanuvchisiz.", show_alert=True)
            await callback.message.answer(f"🎉 Tabriklaymiz! Siz **Premium** statusini oldingiz.\n\nEndi reklamalarsiz foydalana olasiz.", parse_mode="Markdown")
        else:
            await callback.answer("❌ Hisobingizda mablag' yetarli emas. Iltimos, hisobingizni to'ldiring.", show_alert=True)
            await callback.message.answer("Hisobingizni to'ldirish uchun menyudan 'Hisobni to‘ldirish' tugmasini bosing.")
    elif callback.data == "i_paid_premium_card":
        await callback.answer()
        await callback.message.answer("Iltimos, toʻlov chekining skrinshotini yuboring. Adminlar tez orada tekshirib chiqadi.")
        await state.set_state(BotCreationStates.waiting_for_screenshot)
    elif callback.data == "i_paid_deposit":
        await callback.answer()
        await callback.message.answer("Iltimos, toʻlov chekining skrinshotini yuboring. Adminlar tez orada tekshirib chiqadi.")
        await state.set_state(BotCreationStates.waiting_for_screenshot)
    elif callback.data == "admin_bot_list":
        if user_id != callback.bot.dp["ADMIN_ID"]:
            await callback.answer("❌ Sizda bu huquq yo'q.", show_alert=True)
            return
        
        # Bu qatorni o'zgartiring:
        # Eski: keyboard = admin_bot_list_kb()
        # Yangisi:
        keyboard = admin_bot_list_kb(get_multibot_data(), get_bot_creation_time)
        
        await callback.message.edit_text("Botlar ro'yxati:", reply_markup=keyboard)
    elif callback.data.startswith("toggle_bot_"):
        if user_id != callback.bot.dp["ADMIN_ID"]:
            await callback.answer("❌ Sizda bu huquq yo'q.", show_alert=True)
            return
        bot_username = callback.data.split("_")[2]
        multibot_data = get_multibot_data()
        for bot_info in multibot_data:
            if bot_info.get("username") == bot_username:
                bot_info["active"] = not bot_info.get("active", True)
                update_multibot_data(multibot_data)
                status = "✅" if bot_info["active"] else "❌"
                await callback.message.edit_text(f"@{bot_username} holati: {status}")
                break
async def cancel_command(message: types.Message, state: FSMContext):
    """
    Joriy FSM holatini bekor qiladi va foydalanuvchini bosh menyuga qaytaradi.
    """
    await state.clear()
    await message.answer(
        "✅ Amal bekor qilindi. Bosh menyuga qaytdingiz.",
        reply_markup=main_menu
    )

async def process_screenshot(message: types.Message, state: FSMContext, bot: Bot):
    ADMIN_ID = bot.dp["ADMIN_ID"]

    if not message.photo:
        await message.reply("❌ Iltimos, faqat rasm yuboring.")
        return

    user_data = await state.get_data()
    payment_type = user_data.get("payment_type")
    
    # Miqdorni to'g'ri olish uchun o'zgartirilgan qator
    amount = user_data.get("amount") if payment_type else user_data.get("deposit_amount")

    if amount is None:
        await message.answer("❌ To'lov miqdori aniqlanmadi. Iltimos, hisobni to'ldirish jarayonini qaytadan boshlang.")
        await state.clear()
        return

    if payment_type == "bot_creation":
        caption = f"👨‍💻 Yangi bot yaratish to'lovi: {message.from_user.full_name} ({message.from_user.id})\nMiqdor: {amount} so'm"
        callback_data = f"admin_approve:{message.from_user.id}:bot_creation"
    elif payment_type == "monthly":
        caption = f"👨‍💻 Oylik to'lov: {message.from_user.full_name} ({message.from_user.id})\nMiqdor: {amount} so'm"
        callback_data = f"admin_approve:{message.from_user.id}:monthly_card"
    elif payment_type == "premium_card":
        caption = f"👨‍💻 Premium obuna to'lovi: {message.from_user.full_name} ({message.from_user.id})\nMiqdor: {amount} so'm"
        callback_data = f"admin_approve:{message.from_user.id}:premium_card"
    else: # Hisobni to'ldirish
        caption = f"👨‍💻 Yangi hisobni to'ldirish: {message.from_user.full_name} ({message.from_user.id})\nMiqdor: {amount} so'm"
        callback_data = f"admin_approve_deposit:{message.from_user.id}:{amount}"

    try:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=callback_data)]
        ])
        await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=message.photo[-1].file_id,
            caption=caption,
            reply_markup=keyboard
        )
        await message.reply("✅ Skrinshotingiz muvaffaqiyatli qabul qilindi. Admin tasdig'ini kuting.")
        logger.info(f"Foydalanuvchi {message.from_user.id} to'lov uchun skrinshot yubordi.")
    except Exception as e:
        logger.error(f"❌ Skrinshotni adminlarga yuborishda xatolik: {e}")
        await message.reply("❌ Skrinshotni qabul qilishda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
    finally:
        await state.clear()


async def admin_approve_payment(callback_query: types.CallbackQuery, bot: Bot):
    try:
        data = callback_query.data.split(":")
        payment_type = data[0]
        
        if len(data) < 2:
            await callback_query.answer("❌ Ma'lumotlar to'liq emas. Amaliyot bekor qilindi.", show_alert=True)
            return

        user_id_to_approve = int(data[1])
        await callback_query.answer("Tasdiqlash ishlanyapti...", show_alert=False)

        new_caption = f"✅ To'lov tasdiqlandi. Foydalanuvchi: {user_id_to_approve}"
        reply_markup = None
        
        if payment_type == "admin_approve":
            if len(data) < 3:
                await callback_query.answer("❌ To'lov turini aniqlashda xatolik.", show_alert=True)
                return
            transaction_type = data[2]
            
            if transaction_type == "bot_creation":
                await bot.send_message(
                    chat_id=user_id_to_approve,
                    text="✅ To'lovingiz tasdiqlandi!\nBot tokenini yuboring. Token `123456:ABCEFGH...` ko'rinishida bo'ladi."
                )
                
                state_context = FSMContext(
                    storage=bot.dp.storage,
                    key=StorageKey(
                        bot_id=bot.id,
                        chat_id=user_id_to_approve,
                        user_id=user_id_to_approve
                    )
                )
                await state_context.set_state(BotCreationStates.waiting_for_token)
                await state_context.update_data(user_id=user_id_to_approve)
                logger.info(f"Admin to'lovni tasdiqladi, ID: {user_id_to_approve}")
            
            elif transaction_type == "premium_card":
                user_data = get_user_data(user_id_to_approve)
                user_data["status"] = "Premium"
                user_data["donations"] = user_data.get("donations", 0) + 5000
                update_user_data(user_id_to_approve, user_data)
                await bot.send_message(
                    chat_id=user_id_to_approve,
                    text="✅ To'lovingiz tasdiqlandi! Siz endi **Premium** foydalanuvchisiz.",
                    parse_mode="Markdown"
                )
            
            elif transaction_type == "monthly_card":
                user_data = get_user_data(user_id_to_approve)
                user_data["donations"] = user_data.get("donations", 0) + 20000
                update_user_data(user_id_to_approve, user_data)
                await bot.send_message(
                    chat_id=user_id_to_approve,
                    text="✅ Oylik to'lovingiz muvaffaqiyatli bo'ldi!"
                )
            
            # Matnni emas, balki captionni tahrirlash uchun
            await callback_query.message.edit_caption(caption=new_caption, reply_markup=reply_markup)
        
        elif payment_type == "admin_approve_deposit":
            if len(data) < 3:
                await callback_query.answer("❌ To'lov miqdorini aniqlashda xatolik.", show_alert=True)
                return
            
            deposit_amount_str = data[2]
            
            if not deposit_amount_str.isdigit():
                await callback_query.answer("❌ Noto'g'ri to'lov miqdori. Amaliyot bekor qilindi.", show_alert=True)
                return

            deposit_amount = int(deposit_amount_str)
            user_data = get_user_data(user_id_to_approve)
            user_data["balance"] += deposit_amount
            user_data["donations"] += deposit_amount
            update_user_data(user_id_to_approve, user_data)
            await bot.send_message(
                chat_id=user_id_to_approve,
                text=f"✅ Hisobingiz **{deposit_amount} so'm**ga to'ldirildi. Yangi balansingiz: **{user_data['balance']} so'm**",
                parse_mode="Markdown"
            )
            # Matnni emas, balki captionni tahrirlash uchun
            await callback_query.message.edit_caption(caption=f"✅ Hisob to'ldirish tasdiqlandi. Foydalanuvchi: {user_id_to_approve}")
            
    except Exception as e:
        logger.error(f"❌ To'lovni tasdiqlashda xatolik: {e}")
        await callback_query.answer("❌ Xatolik yuz berdi. Iltimos, qayta urining.", show_alert=True)

async def process_bot_token(message: types.Message, state: FSMContext, bot: Bot):
    # Buyruqdan keyingi argumentlar mavjudligini tekshiramiz
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Iltimos, /token buyrug'idan keyin bot tokenini kiriting.")
        return
    
    bot_token = args[1] # Ikkinchi elementni olamiz

    if len(bot_token) > 20 and ":" in bot_token:
        # Eski holatni topish va o'zgartirish
        user_data = await state.get_data()
        bot_username = user_data.get("bot_username")
        
        if bot_username:
            multibot_data = get_multibot_data()
            found = False
            for bot_info in multibot_data:
                if bot_info.get("username") == bot_username:
                    bot_info["bot_token"] = bot_token
                    update_multibot_data(multibot_data)
                    found = True
                    break
            if found:
                await message.answer(f"✅ @{bot_username} uchun bot tokeni muvaffaqiyatli o'zgartirildi.")
            else:
                await message.answer("❌ O'zgartirish uchun bot topilmadi. Qaytadan urinib ko'ring.")
            await state.clear()
        else:
            await state.update_data(bot_token=bot_token)
            await message.answer("✅ Bot token qabul qilindi. Endi botingizning **username**'ini (masalan, `my_super_bot`) yuboring.")
            await state.set_state(BotCreationStates.waiting_for_username)
    else:
        await message.answer("❌ Noto'g'ri token formati. Iltimos, to'g'ri token yuboring.")

async def process_bot_username(message: types.Message, state: FSMContext, bot: Bot):
    bot_username = message.text.strip().replace('@', '')
    user_data = await state.get_data()
    bot_token = user_data.get("bot_token")

    if not bot_token:
        await message.answer("Bot token topilmadi. Iltimos, qaytadan boshlang.")
        await state.clear()
        return

    try:
        temp_bot = Bot(token=bot_token)
        bot_info = await temp_bot.get_me()
        real_username = bot_info.username
        if bot_username.lower() != real_username.lower():
            await message.answer(
                f"❌ Xatolik: Yuborgan username (`@{bot_username}`) botning haqiqiy username'i (`@{real_username}`) bilan mos kelmadi.\n"
                f"Iltimos, to'g'ri username yuboring."
            )
            return
    except Exception as e:
        logger.error(f"Bot haqida ma'lumot olishda xatolik: {e}")
        await message.answer("❌ Bot tokeni bilan aloqa o'rnatishda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
        await state.clear()
        return

    multibot_data = get_multibot_data()
    
    # Username'ni yangilash yoki yangi bot yaratish
    found = False
    for bot_info in multibot_data:
        if bot_info.get("owner_id") == message.from_user.id and bot_info.get("username") == user_data.get("bot_username"):
            bot_info["username"] = bot_username
            update_multibot_data(multibot_data)
            await message.answer(f"✅ Username muvaffaqiyatli o'zgartirildi: @{bot_username}")
            found = True
            break
            
    if not found:
        # Yangi botni saqlash
        current_date = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        multibot_data.append({
            "bot_token": bot_token,
            "username": bot_username,
            "owner_id": message.from_user.id,
            "created_date": current_date
        })
        update_multibot_data(multibot_data)
        await message.answer("Username qabul qilindi. Botingiz ma'lumotlari saqlandi va u ishga tushirilyapti.")
    
    await state.clear()

    try:
        subprocess.Popen(["python", "new_bot.py", bot_token, bot_username])
        logger.info(f"Yangi bot jarayoni ishga tushirildi: @{bot_username}")
    except Exception as e:
        logger.error(f"❌ Botni ishga tushirishda xatolik: {e}")
        await bot.send_message(message.bot.dp["ADMIN_ID"], f"Botni ishga tushirishda xatolik: {e}")

    await bot.send_message(
        message.bot.dp["ADMIN_ID"],
        f"Yangi bot yaratildi:\nToken: `{bot_token}`\nUsername: `@{bot_username}`\nFoydalanuvchi ID: `{message.from_user.id}`"
    )

async def admin_command(message: types.Message):
    ADMIN_ID = message.bot.dp["ADMIN_ID"]
    if message.from_user.id != ADMIN_ID:
        await message.answer("Siz admin emassiz.")
        return
    await message.answer("Admin paneli:", reply_markup=admin_main_kb)

async def process_new_channel_id(message: types.Message, state: FSMContext):
    channel_id = message.text.strip()
    if not channel_id.startswith("-100") or not channel_id[1:].isdigit():
        await message.answer("Noto'g'ri kanal ID'si formati. Iltimos, qayta urinib ko'ring.")
        return
    
    channels = get_admin_channels()
    if channel_id in channels:
        await message.answer("Bu kanal allaqachon ro'yxatga olingan.")
    else:
        channels.append(channel_id)
        save_admin_channels(channels)
        await message.answer("✅ Kanal muvaffaqiyatli qo'shildi!")
    
    await state.clear()

async def check_subscription(callback: types.CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    channels = get_admin_channels()
    
    unsubscribed_channels = []
    
    for channel_id in channels:
        try:
            member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status in ["left", "kicked"]:
                unsubscribed_channels.append(channel_id)
        except Exception as e:
            logger.error(f"❌ Kanal ({channel_id}) a'zoligini tekshirishda xatolik: {e}")
    
    if unsubscribed_channels:
        text = "Siz quyidagi kanallarga obuna bo'lmagansiz:\n\n"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for channel_id in unsubscribed_channels:
            try:
                chat = await bot.get_chat(channel_id)
                invite_link = chat.invite_link
                if not invite_link:
                    invite_link = await chat.create_invite_link()
                keyboard.inline_keyboard.append([InlineKeyboardButton(text=f"@{chat.username}", url=invite_link)])
            except Exception as e:
                logger.error(f"❌ Kanal ma'lumotlarini olishda xatolik: {e}")
                keyboard.inline_keyboard.append([InlineKeyboardButton(text=f"Kanal {channel_id}", url=f"https://t.me/c/{str(channel_id)[4:]}")])

        keyboard.inline_keyboard.append([InlineKeyboardButton(text="✅ Obunani tasdiqlash", callback_data="check_subscription")])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer("Obuna bo'lmagan kanallar mavjud.", show_alert=True)
    else:
        await callback.message.edit_text("🎉 A'zoligingiz tekshirildi! Botdan foydalanishingiz mumkin.", reply_markup=None)
        await callback.answer("✅ Obuna muvaffaqiyatli tasdiqlandi.", show_alert=True)