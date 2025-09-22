import os
import json
import asyncio
import logging
import re
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.exceptions import TelegramNetworkError, TelegramAPIError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.enums import ContentType
from aiogram.filters import StateFilter
from states import BotCreationStates

# Logging sozlash
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Fayl boshqaruvi (bot username'iga bog'langan papka yaratish) ---
def get_filenames(bot_username):
    base_dir = os.path.join("bots_data", bot_username.replace('@', ''))
    os.makedirs(base_dir, exist_ok=True)
    return {
        "data": os.path.join(base_dir, "data.json"),
        "admins": os.path.join(base_dir, "admins.json"),
        "channels": os.path.join(base_dir, "channels.json"),
        "statistics": os.path.join(base_dir, "statistics.json"),
        "movie_info": os.path.join(base_dir, "movie_info.json"),
    }

def ensure_file(filename, default_data):
    if not os.path.exists(filename):
        try:
            with open(filename, "w", encoding='utf-8') as f:
                json.dump(default_data, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ {filename} fayli yaratildi.")
        except Exception as e:
            logger.error(f"❌ {filename} faylini yaratishda xatolik: {e}")

def load_json(filename, default_type):
    try:
        with open(filename, "r", encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {} if default_type == "dict" else []

def save_json(filename, data):
    try:
        with open(filename, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ {filename} fayli saqlandi.")
    except Exception as e:
        logger.error(f"❌ {filename} faylini saqlashda xatolik: {e}")

# Global o'zgaruvchilar
waiting_for_channel = set()
waiting_for_code_data = {}
waiting_for_movie_info = {}
users_count = set()

# --- Klaviaturalar ---
def get_admin_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎬 Kino qo'shish"), KeyboardButton(text="📝 Video tasnifi")],
            [KeyboardButton(text="📢 Kanal qo'shish"), KeyboardButton(text="📢 Asosiy kanal ID'si")],
            [KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="🗑 Kanal o'chirish"), KeyboardButton(text="🗑 Video o'chirish")],
            [KeyboardButton(text="🗑 Ma'lumot o'chirish"), KeyboardButton(text="❌ Tugmalarni yopish")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard

# --- Yordamchi funksiyalar ---
def parse_telegram_url(url):
    try:
        if '/c/' in url:
            match = re.search(r'/c/(\d+)/(\d+)', url)
            if match:
                channel_id = f"-100{match.group(1)}"
                message_id = int(match.group(2))
                return channel_id, message_id
        else:
            match = re.search(r't\.me/([^/]+)/(\d+)', url)
            if match:
                username = f"@{match.group(1)}"
                message_id = int(match.group(2))
                return username, message_id
        return None, None
    except Exception as e:
        logger.error(f"URL parse qilishda xatolik: {e}")
        return None, None

# --- Handlerlar ---
async def start_command(message: types.Message, admins: list, state: FSMContext):
    await state.clear()
    global users_count, channels
    user_id = message.from_user.id
    users_count.add(user_id)
    
    if user_id in admins:
        await message.reply("👨‍💼 Admin paneliga xush kelibsiz!", reply_markup=get_admin_keyboard())
        return

    if channels:
        all_ok = True
        for ch_id in channels:
            try:
                member = await message.bot.get_chat_member(chat_id=ch_id, user_id=user_id)
                if member.status in ["left", "kicked"]:
                    all_ok = False
                    break
            except Exception as e:
                logger.error(f"Obuna tekshirishda xatolik {ch_id}: {e}")
                all_ok = False
                break

        if not all_ok:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[])
            for ch_id in channels:
                try:
                    chat_info = await message.bot.get_chat(ch_id)
                    channel_name = chat_info.title
                    invite_link = chat_info.invite_link
                    keyboard.inline_keyboard.append([InlineKeyboardButton(text=f"📢 {channel_name}", url=invite_link)])
                except Exception as e:
                    logger.error(f"Kanal ma'lumotini olishda xatolik: {e}")
                    keyboard.inline_keyboard.append([InlineKeyboardButton(text="📢 Kanal", url=str(ch_id))])
            
            keyboard.inline_keyboard.append([InlineKeyboardButton(text="✅ Obuna tekshirish", callback_data="check_subscription")])
            await message.reply("👋 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:", reply_markup=keyboard)
            return

    await message.reply("👋 Salom! Kino kodini yuboring.", reply_markup=ReplyKeyboardRemove())

async def register_admin_command(message: types.Message, state: FSMContext):
    global admins
    user_id = message.from_user.id
    if user_id in admins:
        await message.reply("Siz allaqachon adminsiz.")
    else:
        await state.set_state(BotCreationStates.waiting_for_admin_password)
        await message.reply("Admin parolini kiriting:")

async def process_admin_password(message: types.Message, state: FSMContext, filenames: dict):
    global admins
    ADMIN_PASSWORD = "admin123"
    user_id = message.from_user.id
    
    if message.text == ADMIN_PASSWORD:
        if user_id not in admins:
            admins.append(user_id)
            save_json(filenames['admins'], admins)
            await message.reply("✅ Siz admin bo'ldingiz! Endi admin paneldan foydalaning.", reply_markup=get_admin_keyboard())
            logger.info(f"Yangi admin tayinlandi: {user_id}")
        else:
            await message.reply("Siz allaqachon adminsiz.", reply_markup=get_admin_keyboard())
        await state.clear()
    else:
        await message.reply("❌ Noto'g'ri parol. Qayta urinib ko'ring yoki /cancel buyrug'i bilan bekor qiling.")

async def process_channel_id(message: types.Message, state: FSMContext, filenames: dict):
    global channels
    channel_id = message.text.strip()
    user_id = message.from_user.id

    if not (channel_id.startswith('-100') or channel_id.startswith('@')):
        await message.reply("❌ Noto'g'ri kanal formati. Masalan: -1001234567890 yoki @kanal_username. Qayta yuboring.")
        return

    if channels:
        channels.clear()  # Eski kanal ID'sini o'chirib tashlash
    channels.append(channel_id)
    save_json(filenames['channels'], channels)
    await message.reply(f"✅ Asosiy kanal ID'si yangilandi: {channel_id}.", reply_markup=get_admin_keyboard())
    logger.info(f"Asosiy kanal ID'si yangilandi: {channel_id}")
    await state.clear()

async def handle_admin_buttons(message: types.Message, admins: list, state: FSMContext):
    global waiting_for_channel, waiting_for_code_data, waiting_for_movie_info, film_data, channels, statistics, movie_info, users_count
    user_id = message.from_user.id
    text = message.text

    if user_id not in admins:
        await message.reply("❌ Sizda admin huquqlari yo'q.")
        return

    if text == "🎬 Kino qo'shish":
        await message.reply("Kino qo'shish uchun kod va video ma'lumotlarini yuboring:\nFormat: `kod message_id` yoki `kod https://t.me/kanal/123`")
        waiting_for_code_data[user_id] = True
    elif text == "📝 Video tasnifi":
        await message.reply("Video tasnifi qo'shish uchun ma'lumotlarni yuboring:\nFormat: `kod Nomi|Janri|Tili|Davomiyligi`")
        waiting_for_movie_info[user_id] = True
    elif text == "📢 Kanal qo'shish":
        await message.reply("Kanal ID yoki linkini yuboring.")
        waiting_for_channel.add(user_id)
    elif text == "📢 Asosiy kanal ID'si":
        await message.reply("Asosiy kanal ID'sini kiriting (masalan, -1001234567890 yoki @kanal_username):")
        await state.set_state(BotCreationStates.waiting_for_channel_id)
    elif text == "📊 Statistika":
        total_movies = len(film_data)
        total_downloads = sum(stats.get("downloads", 0) for stats in statistics.values())
        total_channels = len(channels)
        total_users = len(users_count)
        stats_text = (
            f"📊 **Bot Statistikasi**\n\n"
            f"👥 Jami foydalanuvchilar: {total_users}\n"
            f"🎬 Jami kinolar: {total_movies}\n"
            f"⬇️ Jami yuklab olishlar: {total_downloads}\n"
            f"📢 Kanallar soni: {total_channels}\n"
            f"👨‍💼 Adminlar soni: {len(admins)}"
        )
        if statistics:
            stats_text += "\n\n📈 **Eng ommabop kinolar:**\n"
            sorted_movies = sorted(statistics.items(), key=lambda x: x[1].get("downloads", 0), reverse=True)[:5]
            for i, (code, stats) in enumerate(sorted_movies, 1):
                movie_name = movie_info.get(code, {}).get("name", f"Kod: {code}")
                downloads = stats.get("downloads", 0)
                stats_text += f"{i}. {movie_name} - {downloads} marta\n"
        await message.reply(stats_text)
    elif text == "🗑 Kanal o'chirish":
        if not channels:
            await message.reply("❌ Hech qanday kanal mavjud emas.")
            return
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"🗑 {ch_id}", callback_data=f"delete_channel_{ch_id}")] for ch_id in channels])
        await message.reply("O'chirish uchun kanalni tanlang:", reply_markup=keyboard)
    elif text == "🗑 Video o'chirish":
        if not film_data:
            await message.reply("❌ Hech qanday video mavjud emas.")
            return
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"🗑 {movie_info.get(code, {}).get('name', f'Kod: {code}')}", callback_data=f"delete_video_{code}")] for code in film_data])
        await message.reply("O'chirish uchun videoni tanlang:", reply_markup=keyboard)
    elif text == "🗑 Ma'lumot o'chirish":
        if not movie_info:
            await message.reply("❌ Hech qanday ma'lumot mavjud emas.")
            return
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"🗑 {info.get('name', f'Kod: {code}')}", callback_data=f"delete_info_{code}")] for code, info in movie_info.items()])
        await message.reply("O'chirish uchun ma'lumotni tanlang:", reply_markup=keyboard)
    elif text == "❌ Tugmalarni yopish":
        await message.reply("Admin tugmalari yopildi.", reply_markup=ReplyKeyboardRemove())

async def handle_text(message: types.Message, admins: list, filenames: dict):
    global waiting_for_channel, waiting_for_code_data, waiting_for_movie_info, film_data, channels, statistics, movie_info, users_count
    user_id = message.from_user.id
    text = message.text.strip()
    users_count.add(user_id)

    if user_id in waiting_for_code_data:
        if user_id not in admins:
            await message.reply("❌ Sizda admin huquqlari yo'q.")
            del waiting_for_code_data[user_id]
            return
        parts = text.split(maxsplit=1)
        if len(parts) != 2:
            await message.reply("❌ Format noto'g'ri. Misol: 123 456 yoki 123 https://t.me/kanal/456")
            return
        code, value = parts[0], parts[1]
        try:
            if value.startswith('http'):
                film_data[code] = value
            else:
                film_data[code] = int(value)
            save_json(filenames['data'], film_data)
            if code not in statistics:
                statistics[code] = {"downloads": 0}
                save_json(filenames['statistics'], statistics)
            await message.reply(f"✅ Kino kodi '{code}' saqlandi.")
            del waiting_for_code_data[user_id]
        except ValueError:
            await message.reply("❌ Message ID raqam bo'lishi kerak yoki to'g'ri URL kiriting.")
        return

    if user_id in waiting_for_channel:
        if user_id not in admins:
            await message.reply("❌ Sizda admin huquqlari yo'q.")
            waiting_for_channel.remove(user_id)
            return
        if text not in channels:
            channels.append(text)
            save_json(filenames['channels'], channels)
            await message.reply(f"✅ Kanal qo'shildi: {text}")
        else:
            await message.reply("❗ Bu link allaqachon mavjud.")
        waiting_for_channel.remove(user_id)
        return

    if user_id in waiting_for_movie_info:
        if user_id not in admins:
            await message.reply("❌ Sizda admin huquqlari yo'q.")
            del waiting_for_movie_info[user_id]
            return
        parts = text.split(maxsplit=1)
        if len(parts) != 2 or '|' not in parts[1]:
            await message.reply("❌ Format noto'g'ri. Misol: `123 Spiderman|Fantastika|Ingliz tili|2 soat`")
            return
        code, info_text = parts[0], parts[1]
        info_parts = info_text.split('|')
        if code not in film_data:
            await message.reply("❌ Bu kod mavjud emas. Avval kino qo'shing.")
            return
        movie_info[code] = {"name": info_parts[0].strip(), "genre": info_parts[1].strip(), "language": info_parts[2].strip(), "duration": info_parts[3].strip()}
        save_json(filenames['movie_info'], movie_info)
        await message.reply(f"✅ Kino ma'lumotlari saqlandi:\n\n🎬 **{movie_info[code]['name']}**")
        del waiting_for_movie_info[user_id]
        return

    if text.isdigit():
        await send_video_with_info(message, text, film_data, statistics, movie_info, channels)
    else:
        await message.reply("❓ Noma'lum buyruq. Kino kodini yuboring yoki /start bosing.")

async def send_video_with_info(message: types.Message, code: str, film_data: dict, statistics: dict, movie_info: dict, channels: list):
    user_id = message.from_user.id
    if code not in film_data:
        await message.reply("❌ Bu kod bo'yicha kino topilmadi.")
        return

    if code not in statistics:
        statistics[code] = {"downloads": 0}
    statistics[code]["downloads"] += 1
    save_json(filenames['statistics'], statistics)

    video_data = film_data[code]
    caption = ""
    if code in movie_info:
        info = movie_info[code]
        downloads = statistics[code]["downloads"]
        caption = f"🎬 **{info['name']}**\n\n🎭 Janri: {info['genre']}\n🌐 Tili: {info['language']}\n⏱ Davomiyligi: {info['duration']}\n📊 Yuklab olishlar: {downloads}"

    try:
        if isinstance(video_data, str) and video_data.startswith('http'):
            channel_id, message_id = parse_telegram_url(video_data)
            await message.bot.copy_message(chat_id=user_id, from_chat_id=channel_id, message_id=message_id, caption=caption, parse_mode="Markdown")
        else:
            if channels:
                channel_id_to_copy = channels[0]  # Har bot uchun alohida kanal, birinchisini olish
                await message.bot.copy_message(chat_id=user_id, from_chat_id=channel_id_to_copy, message_id=video_data, caption=caption, parse_mode="Markdown")
            else:
                await message.reply("❌ Kino kanali sozlanmagan. Admin bilan bog'laning.")
                logger.error("Kino kanali topilmadi. 'channels' ro'yxati bo'sh.")
    except Exception as e:
        logger.error(f"Kino yuborishda xatolik: {e}")
        await message.reply("❌ Kino yuborishda xatolik yuz berdi.")

async def check_subscription(callback_query: types.CallbackQuery, channels: list):
    user_id = callback_query.from_user.id
    all_ok = True
    for ch_id in channels:
        try:
            if str(ch_id).startswith('@') or str(ch_id).startswith('-') or str(ch_id).isdigit():
                member = await callback_query.bot.get_chat_member(chat_id=ch_id, user_id=user_id)
                if member.status in ["left", "kicked"]:
                    all_ok = False
                    break
        except Exception as e:
            logger.error(f"Obuna tekshirishda xatolik {ch_id}: {e}")
            all_ok = False
            break

    if all_ok:
        await callback_query.message.edit_text("✅ A'zoligingiz tasdiqlandi. Kino kodini yuborishingiz mumkin.", reply_markup=None)
    else:
        await callback_query.answer("❌ Siz barcha kanallarga obuna bo'lmagansiz!", show_alert=True)

async def handle_delete_channel(callback_query: types.CallbackQuery, admins: list, filenames: dict):
    global channels
    user_id = callback_query.from_user.id
    if user_id not in admins:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q.", show_alert=True)
        return

    channel_id_to_delete = callback_query.data.split("_")[2]
    if channel_id_to_delete in channels:
        channels.remove(channel_id_to_delete)
        save_json(filenames['channels'], channels)
        await callback_query.message.edit_text(f"✅ Kanal '{channel_id_to_delete}' o'chirildi.")
    else:
        await callback_query.answer("❌ Kanal topilmadi!", show_alert=True)

async def handle_delete_video(callback_query: types.CallbackQuery, admins: list, filenames: dict):
    global film_data, statistics, movie_info
    user_id = callback_query.from_user.id
    if user_id not in admins:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q.", show_alert=True)
        return

    code_to_delete = callback_query.data.split("_")[2]
    if code_to_delete in film_data:
        del film_data[code_to_delete]
        save_json(filenames['data'], film_data)
        if code_to_delete in statistics:
            del statistics[code_to_delete]
            save_json(filenames['statistics'], statistics)
        if code_to_delete in movie_info:
            del movie_info[code_to_delete]
            save_json(filenames['movie_info'], movie_info)
        await callback_query.message.edit_text(f"✅ Kino '{code_to_delete}' o'chirildi.")
    else:
        await callback_query.answer("❌ Kino topilmadi!", show_alert=True)

async def handle_delete_info(callback_query: types.CallbackQuery, admins: list, filenames: dict):
    global movie_info
    user_id = callback_query.from_user.id
    if user_id not in admins:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q.", show_alert=True)
        return

    code_to_delete = callback_query.data.split("_")[2]
    if code_to_delete in movie_info:
        del movie_info[code_to_delete]
        save_json(filenames['movie_info'], movie_info)
        await callback_query.message.edit_text(f"✅ Ma'lumot '{code_to_delete}' o'chirildi.")
    else:
        await callback_query.answer("❌ Ma'lumot topilmadi!", show_alert=True)

# --- Botni ishga tushirish qismi ---
async def main():
    if len(sys.argv) < 3:
        logger.error("Bot tokeni va username berilmagan.")
        return

    bot_token = sys.argv[1]
    bot_username = sys.argv[2]
    
    global bot, dp, filenames, film_data, admins, channels, statistics, movie_info
    
    filenames = get_filenames(bot_username)
    ensure_file(filenames["data"], {})
    ensure_file(filenames["admins"], [])
    ensure_file(filenames["channels"], [])
    ensure_file(filenames["statistics"], {})
    ensure_file(filenames["movie_info"], {})
    
    film_data = load_json(filenames["data"], "dict")
    admins = load_json(filenames["admins"], "list")
    channels = load_json(filenames["channels"], "list")
    statistics = load_json(filenames["statistics"], "dict")
    movie_info = load_json(filenames["movie_info"], "dict")

    bot = Bot(token=bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    dp["admins"] = admins
    dp["filenames"] = filenames
    dp["film_data"] = film_data
    dp["channels"] = channels
    dp["statistics"] = statistics
    dp["movie_info"] = movie_info
    dp["waiting_for_channel"] = waiting_for_channel
    dp["waiting_for_code_data"] = waiting_for_code_data
    dp["waiting_for_movie_info"] = waiting_for_movie_info
    dp["users_count"] = users_count

    dp.message.register(start_command, Command("start"))
    dp.message.register(register_admin_command, Command("register_admin"))
    dp.message.register(process_admin_password, StateFilter(BotCreationStates.waiting_for_admin_password))
    dp.message.register(process_channel_id, StateFilter(BotCreationStates.waiting_for_channel_id))
    dp.message.register(handle_admin_buttons, F.text.in_(["🎬 Kino qo'shish", "📝 Video tasnifi", "📢 Kanal qo'shish", "📢 Asosiy kanal ID'si", "📊 Statistika", "🗑 Kanal o'chirish", "🗑 Video o'chirish", "🗑 Ma'lumot o'chirish", "❌ Tugmalarni yopish"]))
    dp.message.register(handle_text, F.text)
    dp.callback_query.register(check_subscription, F.data == "check_subscription")
    dp.callback_query.register(handle_delete_channel, F.data.startswith("delete_channel_"))
    dp.callback_query.register(handle_delete_video, F.data.startswith("delete_video_"))
    dp.callback_query.register(handle_delete_info, F.data.startswith("delete_info_"))
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())