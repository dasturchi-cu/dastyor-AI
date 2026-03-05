from telegram import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from bot.utils.i18n import t


def get_main_menu(user_id=None, lang="uz_lat"):
    """
    Main menu — 4 clear buttons for mobile.
    Layout:
      [ Obyektivka ]  [ CV Resume ]
      [   Balans   ]  [ Boshqa xizmatlar ]
    """
    keyboard = [
        [
            KeyboardButton(t("btn_oby", lang)),
            KeyboardButton(t("btn_cv", lang)),
        ],
        [
            KeyboardButton(t("btn_balance", lang)),
            KeyboardButton(t("btn_more", lang)),
        ],
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_more_menu(lang="uz_lat"):
    """
    'Boshqa xizmatlar' sub-menu — 6 buttons.
    Layout:
      [ Krill-Lotin   ]  [ Rasm → PDF     ]
      [ Imlo tekshirish] [ Tarjima        ]
      [ Rasm → Word AI]  [ Aloqa          ]
      [ ← Orqaga                          ]
    """
    keyboard = [
        [
            KeyboardButton(t("btn_translit", lang)),
            KeyboardButton(t("btn_pdf", lang)),
        ],
        [
            KeyboardButton(t("btn_spell", lang)),
            KeyboardButton(t("btn_translate", lang)),
        ],
        [
            KeyboardButton(t("btn_ocr", lang)),
            KeyboardButton(t("btn_contact", lang)),
        ],
        [
            KeyboardButton(t("back_to_menu", lang)),
        ],
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_krill_lotin_menu(lang="uz_lat"):
    """Kirill-Lotin conversion sub-menu"""
    keyboard = [
        [
            KeyboardButton("🔡 Kirill → Lotin"),
            KeyboardButton("🔠 Lotin → Kirill"),
        ],
        [KeyboardButton(t("back_to_menu", lang))],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_translate_menu(lang="uz_lat"):
    """Translation language selection menu — 5 directions"""
    keyboard = [
        [
            KeyboardButton("🇺🇿 O'zbek → Ingliz"),
            KeyboardButton("🇬🇧 Ingliz → O'zbek"),
        ],
        [
            KeyboardButton("🇷🇺 Rus → O'zbek"),
            KeyboardButton("O'zbek → Rus 🇷🇺"),
        ],
        [
            KeyboardButton("Rus → Ingliz"),
        ],
        [KeyboardButton(t("back_to_menu", lang))],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_back_button(lang="uz_lat"):
    """Simple back button"""
    keyboard = [[KeyboardButton(t("back_to_menu", lang))]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_image_to_pdf_keyboard(lang="uz_lat"):
    """Keyboard for Rasm → PDF flow"""
    keyboard = [
        [KeyboardButton("✅ Tayyor — PDF tuzish")],
        [KeyboardButton(t("back_to_menu", lang))],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)