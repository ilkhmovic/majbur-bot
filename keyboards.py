from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# Bosh menyu
main_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🤖 Botlarni boshqarish")],
    [KeyboardButton(text="➕ Hisobni to‘ldirish"), KeyboardButton(text="👤 Kabinet")],
    [KeyboardButton(text="📖 Qo‘llanma"), KeyboardButton(text="🆘 Yordam")]
], resize_keyboard=True)

# Botlarni boshqarish menyusi
manage_bot_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🆕 Bot yaratish"), KeyboardButton(text="⚙️ Bot sozlash")],
    [KeyboardButton(text="🔙 Ortga qaytish")]
], resize_keyboard=True)

# To'lovni tasdiqlash uchun
i_agree_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ Rozi bo'ldim", callback_data="i_agree_to_pay")]
])

paid_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ To'ladim", callback_data="i_paid")]
])

# Kabinet menyusi
cabinet_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💎 Premium sotib olish", callback_data="buy_premium")],
])

# To'lov turlari uchun klaviatura
payment_options_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💳 Karta orqali", callback_data="pay_with_card")],
    [InlineKeyboardButton(text="💰 Balansdan", callback_data="pay_with_balance")]
])

# Kartadan to'lovni tasdiqlash
card_payment_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ To'ladim", callback_data="i_paid_premium_card")]
])

# Hisobni to'ldirish uchun klaviatura
deposit_card_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ To'ladim", callback_data="i_paid_deposit")]
])

# Bot sozlamalari klaviaturasi
def bot_settings_kb(bot_username):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Tokenni o'zgartirish", callback_data=f"change_token_{bot_username}")],
        [InlineKeyboardButton(text="✏️ Username'ni o'zgartirish", callback_data=f"change_username_{bot_username}")],
        [InlineKeyboardButton(text="💳 Oylik to'lov", callback_data=f"pay_monthly_{bot_username}")]
    ])

def bot_payment_options_kb(bot_username):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Karta orqali", callback_data="pay_with_card_monthly")],
        [InlineKeyboardButton(text="💰 Balansdan", callback_data="pay_with_balance_monthly")],
        [InlineKeyboardButton(text="Ortga", callback_data=f"select_bot_0")]
    ])

# Admin botlar ro'yxati
def admin_bot_list_kb(multibot_data, get_bot_creation_time):
    keyboard = []
    for bot_info in multibot_data:
        status = "✅" if bot_info.get("active", True) else "❌"
        creation_time = get_bot_creation_time(bot_info['username'])
        keyboard.append([InlineKeyboardButton(
            text=f"{status} @{bot_info['username']} (Yaratilgan: {creation_time})",
            callback_data=f"toggle_bot_{bot_info['username']}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

admin_main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📢 Kanal qo'shish"), KeyboardButton(text="🗑 Kanal o'chirish")],
    [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="❌ Tugmalarni yopish")]
], resize_keyboard=True)

def admin_channels_kb(channels):
    buttons = []
    for i, channel_id in enumerate(channels):
        buttons.append([InlineKeyboardButton(text=f"🗑 Kanal {i+1} ({channel_id})", callback_data=f"delete_channel:{channel_id}")])
    buttons.append([InlineKeyboardButton(text="➕ Yangi kanal qo'shish", callback_data="add_new_channel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)