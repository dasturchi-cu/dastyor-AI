"""Centralized bot message templates for consistent UX tone."""

WELCOME_TEXT = (
    "Assalomu alaykum.\n\n"
    "Formani to'ldirish uchun xizmatni tanlang:\n"
    "• CV Resume\n"
    "• Obyektivka"
)

HELP_TEXT = (
    "ℹ️ Yordam\n\n"
    "1) CV Resume — CV forma ochiladi\n"
    "2) Obyektivka — obyektivka forma ochiladi\n"
    "3) Murojaat — admin bilan bog'lanish\n\n"
    "Bekor qilish uchun: 'bekor' deb yozing."
)

SUPPORT_START_TEXT = (
    "📩 Murojaat yuborish\n\n"
    "Yuborishingiz mumkin:\n"
    "• Matn\n"
    "• Rasm\n"
    "• Ovozli xabar\n"
    "• Fayl\n\n"
    "Yechim tez bo'lishi uchun muammoni aniq yozing."
)

SUPPORT_SUCCESS_TEXT = (
    "✅ Murojaatingiz qabul qilindi.\n"
    "Admin tez orada javob beradi.\n\n"
    "Yangi xizmat tanlash uchun /menu ni bosing."
)

SUPPORT_INVALID_TEXT = (
    "⚠️ Bu format qabul qilinmadi.\n"
    "Matn, rasm, ovoz yoki fayl yuboring."
)

SUPPORT_CANCEL_TEXT = "↩️ Murojaat rejimi yopildi."

UNKNOWN_INPUT_TEXT = (
    "🤖 Tushundim, lekin bu buyruqni taniy olmadim.\n\n"
    "Davom etish uchun quyidagilardan birini tanlang:\n"
    "• CV Resume\n"
    "• Obyektivka\n"
    "• Murojaat\n"
    "• Yordam"
)

ADMIN_PANEL_OPENED_TEXT = (
    "🛠 Admin panel ochildi.\n"
    "Kerakli bo'limni tanlang."
)

ADMIN_ONLY_TEXT = "⛔ Bu bo'lim faqat adminlar uchun."

ADMIN_STATUS_TEXT = "✅ Bot holati: barqaror va ishchi."
