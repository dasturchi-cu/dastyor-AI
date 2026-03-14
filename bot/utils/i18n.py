import re

# Bot faqat o'zbek tilida ishlaydi — o'zgartirish mumkin emas
DEFAULT_LANG = "uz_lat"

_DICT = {
    # welcome text
    "welcome": {
        "uz_lat": "Assalomu alaykum, {name}! 👋\n\n📌 <b>DASTYOR AI</b> — hujjat va AI xizmatlar platformasi.\n\nQuyidagi xizmatlardan birini tanlang yoki Mini Appni oching:",
        "uz_cyr": "Ассалому алайкум, {name}! 👋\n\n📌 <b>DASTYOR AI</b> — ҳужжат ва AI хизматлар платформаси.\n\nҚуйидаги хизматлардан бирини танланг ёки Mini Appни очинг:",
        "en": "Hello, {name}! 👋\n\n📌 <b>DASTYOR AI</b> — Documents & AI services platform.\n\nChoose a service below or open the Mini App:",
        "ru": "Здравствуйте, {name}! 👋\n\n📌 <b>DASTYOR AI</b> — Платформа документов и ИИ сервисов.\n\nВыберите услугу ниже или откройте Mini App:"
    },
    
    # Main menu buttons
    "btn_app": {
        "uz_lat": "🚀 Appni ochish",
        "uz_cyr": "🚀 Appни очиш",
        "en": "🚀 Open App",
        "ru": "🚀 Открыть приложение"
    },
    "btn_cv": {
        "uz_lat": "📄 CV Resume",
        "uz_cyr": "📄 CV Resume",
        "en": "📄 CV Resume",
        "ru": "📄 CV Резюме"
    },
    "btn_more": {
        "uz_lat": "🔧 Boshqa xizmatlar",
        "uz_cyr": "🔧 Бошқа хизматлар",
        "en": "🔧 More Services",
        "ru": "🔧 Другие услуги"
    },
    "btn_oby": {
        "uz_lat": "📋 Obyektivka",
        "uz_cyr": "📋 Объективка",
        "en": "📋 CV Record",
        "ru": "📋 Анкета"
    },
    "btn_ocr": {
        "uz_lat": "👁️ OCR",
        "uz_cyr": "👁️ OCR",
        "en": "👁️ OCR",
        "ru": "👁️ OCR"
    },
    "btn_pdf": {
        "uz_lat": "🖼 Rasm→PDF",
        "uz_cyr": "🖼 Расм→PDF",
        "en": "🖼 Image→PDF",
        "ru": "🖼 Изображение→PDF"
    },
    "btn_premium": {
        "uz_lat": "💎 Premium",
        "uz_cyr": "💎 Premium",
        "en": "💎 Premium",
        "ru": "💎 Премиум"
    },
    "btn_translit": {
        "uz_lat": "🔤 Krill-Lotin",
        "uz_cyr": "🔤 Кирилл-Лотин",
        "en": "🔤 Cyrillic-Latin",
        "ru": "🔤 Кириллица-Латиница"
    },
    "btn_translate": {
        "uz_lat": "🌐 Tarjima",
        "uz_cyr": "🌐 Таржима",
        "en": "🌐 Translate",
        "ru": "🌐 Перевод"
    },
    "btn_spell": {
        "uz_lat": "✏️ Imlo tekshirish",
        "uz_cyr": "✏️ Имло текшириш",
        "en": "✏️ Spell Check",
        "ru": "✏️ Проверка орфографии"
    },
    "btn_balance": {
        "uz_lat": "💰 Balans",
        "uz_cyr": "💰 Баланс",
        "en": "💰 Balance",
        "ru": "💰 Баланс"
    },
    "btn_contact": {
        "uz_lat": "✉️ Aloqa",
        "uz_cyr": "✉️ Алоқа",
        "en": "✉️ Contact",
        "ru": "✉️ Контакты"
    },
    "btn_help": {
        "uz_lat": "🆘 Yordam",
        "uz_cyr": "🆘 Ёрдам",
        "en": "🆘 Help",
        "ru": "🆘 Помощь"
    },
    "back_to_menu": {
        "uz_lat": "🔙 Orqaga",
        "uz_cyr": "🔙 Орқага",
        "en": "🔙 Back",
        "ru": "🔙 Назад"
    },
    "more_menu_title": {
        "uz_lat": "🔧 Boshqa xizmatlarni tanlang:",
        "uz_cyr": "🔧 Бошқа хизматларни танланг:",
        "en": "🔧 Choose a service:",
        "ru": "🔧 Выберите услугу:"
    },
    "or_menu": {
        "uz_lat": "👇 Yoki menyudan tanlang:",
        "uz_cyr": "👇 Ёки менюдан танланг:",
        "en": "👇 Or select from menu:",
        "ru": "👇 Или выберите в меню:"
    },

    "balance_msg": {
        "uz_lat": "💰 **Sizning Balansingiz**\n\n👤 ID: `{user_id}`\n📊 Status: **{status}**\n📉 Limit: **{limit_text}**\n📄 Ishlangan fayllar: **{files}** ta\n\nPremium olish uchun: '{premium_btn}' tugmasini bosing.",
        "uz_cyr": "💰 **Сизнинг Балансингиз**\n\n👤 ID: `{user_id}`\n📊 Status: **{status}**\n📉 Лимит: **{limit_text}**\n📄 Ишланган файллар: **{files}** та\n\nPremium олиш учун: '{premium_btn}' тугмасини босинг.",
        "en": "💰 **Your Balance**\n\n👤 ID: `{user_id}`\n📊 Status: **{status}**\n📉 Limit: **{limit_text}**\n📄 Processed files: **{files}**\n\nTo get Premium: Click '{premium_btn}'.",
        "ru": "💰 **Ваш Баланс**\n\n👤 ID: `{user_id}`\n📊 Статус: **{status}**\n📉 Лимит: **{limit_text}**\n📄 Обработано файлов: **{files}** шт\n\nДля получения Premium: Нажмите кнопку '{premium_btn}'."
    },
    "status_prem": {
        "uz_lat": "💎 Premium", "uz_cyr": "💎 Premium", "en": "💎 Premium", "ru": "💎 Премиум"
    },
    "status_free": {
        "uz_lat": "🆓 Oddiy", "uz_cyr": "🆓 Оддий", "en": "🆓 Free", "ru": "🆓 Обычный"
    },
    "limit_unlim": {
         "uz_lat": "♾️ Cheksiz", "uz_cyr": "♾️ Чексиз", "en": "♾️ Unlimited", "ru": "♾️ Безлимит"
    },
    "limit_daily": {
         "uz_lat": "{limit} ta/kun", "uz_cyr": "{limit} та/кун", "en": "{limit} per day", "ru": "{limit} в день"
    },
    "contact_msg": {
        "uz_lat": "📞 **Aloqa uchun:**\n\nAdmin: @DastyorAI\\_Admin\nTexnik yordam: @DastyorSupport\n\nSavol yoki takliflaringizni yozib qoldirishingiz mumkin.",
        "uz_cyr": "📞 **Алоқа учун:**\n\nАдмин: @DastyorAI\\_Admin\nТехник ёрдам: @DastyorSupport\n\nСавол ёки таклифларингизни ёзиб қолдиришингиз мумкин.",
        "en": "📞 **Contact:**\n\nAdmin: @DastyorAI\\_Admin\nTech Support: @DastyorSupport\n\nYou can send your questions or suggestions.",
        "ru": "📞 **Связь:**\n\nАдмин: @DastyorAI\\_Admin\nТехподдержка: @DastyorSupport\n\nМожете оставить ваши вопросы или предложения."
    },
    "opening_service": {
        "uz_lat": "🤖 Tushundim! **{service}** xizmatini ochyapman...",
        "uz_cyr": "🤖 Тушундим! **{service}** хизматини очяпман...",
        "en": "🤖 Got it! Opening **{service}**...",
        "ru": "🤖 Понял! Открываю **{service}**..."
    },
    "unknown_cmd": {
        "uz_lat": "❓ Tushunmadim. Menyudan bo'lim tanlang yoki aniqroq yozing.",
        "uz_cyr": "❓ Тушунмадим. Менюдан бўлим танланг ёки аниқроқ ёзинг.",
        "en": "❓ I didn't understand. Select from menu or write clear.",
        "ru": "❓ Не понял. Выберите из меню или напишите точнее."
    }
}

def get_regex_for_key(key: str) -> str:
    """Kalit uchun barcha til variantlarini qamrab oluvchi regex pattern qaytaradi."""
    entry = _DICT.get(key)
    if not entry:
        return re.escape(key)
    patterns = [re.escape(v) for v in entry.values() if v]
    return "^(" + "|".join(patterns) + ")$"


def t(key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
    # Bot har doim o'zbek tilida — lang parametri e'tiborga olinmaydi
    entry = _DICT.get(key)
    if not entry:
        return key
    text = entry.get(DEFAULT_LANG) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
