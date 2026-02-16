from telegram import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu():
    """
    Returns the main grid menu matching the design from the screenshot.
    Layout: 2x4 grid + 1 full-width button
    """
    keyboard = [
        [
            KeyboardButton("Obyektivka Ai ✨"),
            KeyboardButton("Rasm→Word AI ✨")
        ],
        [
            KeyboardButton("Krill-lotin ✏️"),
            KeyboardButton("Tarjima fayl 📦")
        ],
        [
            KeyboardButton("Rasm→PDF"),
            KeyboardButton("Imlo tekshirish ✏️")
        ],
        [
            KeyboardButton("Premium xizmatlar 💎")
        ],
        [
            KeyboardButton("Balans 💰"),
            KeyboardButton("Aloqa ✉️"),
            KeyboardButton("Yordam 🆘")
        ]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_krill_lotin_menu():
    """Kirill-Lotin conversion menu"""
    keyboard = [
        [
            KeyboardButton("Kirill → Lotin"),
            KeyboardButton("Lotin → Kirill")
        ],
        [KeyboardButton("🔙 Orqaga")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_translate_menu():
    """Translation language selection menu"""
    keyboard = [
        [
            KeyboardButton("O'zbek → Ingliz"),
            KeyboardButton("Ingliz → O'zbek")
        ],
        [
            KeyboardButton("Rus → O'zbek"),
            KeyboardButton("O'zbek → Rus")
        ],
        [
            KeyboardButton("Rus → Ingliz")
        ],
        [KeyboardButton("🔙 Orqaga")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_back_button():
    """Simple back button"""
    keyboard = [[KeyboardButton("🔙 Orqaga")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_image_to_pdf_keyboard():
    """Keyboard for Rasm → PDF flow (Tayyor + Orqaga)"""
    keyboard = [
        [KeyboardButton("Tayyor")],
        [KeyboardButton("🔙 Orqaga")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)