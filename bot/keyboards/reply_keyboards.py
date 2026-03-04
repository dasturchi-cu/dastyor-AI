from telegram import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from bot.utils.i18n import t


def get_main_menu(user_id=None, lang="uz_lat"):
    """
    Returns the main menu grid matching plan.md exactly, translated.
    9 service buttons + webapp launcher.
    """
    base_url = "https://dastyor-ai.onrender.com/webapp/index.html"
    web_app_url = f"{base_url}?telegram_id={user_id}&lang={lang}" if user_id else f"{base_url}?lang={lang}"

    keyboard = [
        [
            KeyboardButton(t("btn_app", lang), web_app=WebAppInfo(url=web_app_url))
        ],
        [
            KeyboardButton(t("btn_oby", lang)),
            KeyboardButton(t("btn_ocr", lang))
        ],
        [
            KeyboardButton(t("btn_translit", lang)),
            KeyboardButton(t("btn_translate", lang))
        ],
        [
            KeyboardButton(t("btn_pdf", lang)),
            KeyboardButton(t("btn_spell", lang))
        ],
        [
            KeyboardButton(t("btn_premium", lang))
        ],
        [
            KeyboardButton(t("btn_balance", lang)),
            KeyboardButton(t("btn_contact", lang)),
            KeyboardButton(t("btn_help", lang))
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