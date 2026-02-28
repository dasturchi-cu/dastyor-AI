from telegram import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo


def get_main_menu():
    """
    Returns the main menu grid matching plan.md exactly.
    9 service buttons + webapp launcher.
    """
    web_app_url = "https://dastyor-ai.onrender.com/webapp/index.html"

    keyboard = [
        [
            KeyboardButton("🚀 Appni ochish", web_app=WebAppInfo(url=web_app_url))
        ],
        [
            KeyboardButton("📋 Obyektivka AI"),
            KeyboardButton("📄 Rasm→Word AI")
        ],
        [
            KeyboardButton("🔤 Krill-Lotin"),
            KeyboardButton("🌐 Tarjima fayl")
        ],
        [
            KeyboardButton("🖼 Rasm→PDF"),
            KeyboardButton("✏️ Imlo tekshirish")
        ],
        [
            KeyboardButton("💎 Premium xizmatlar")
        ],
        [
            KeyboardButton("💰 Balans"),
            KeyboardButton("✉️ Aloqa"),
            KeyboardButton("🆘 Yordam")
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
            KeyboardButton("🔡 Kirill → Lotin"),
            KeyboardButton("🔠 Lotin → Kirill")
        ],
        [KeyboardButton("🔙 Orqaga")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_translate_menu():
    """Translation language selection menu — 5 directions per plan.md"""
    keyboard = [
        [
            KeyboardButton("🇺🇿 O'zbek → Ingliz"),
            KeyboardButton("🇬🇧 Ingliz → O'zbek")
        ],
        [
            KeyboardButton("🇷🇺 Rus → O'zbek"),
            KeyboardButton("O'zbek → Rus 🇷🇺")
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
    """Keyboard for Rasm → PDF flow"""
    keyboard = [
        [KeyboardButton("✅ Tayyor — PDF tuzish")],
        [KeyboardButton("🔙 Orqaga")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)