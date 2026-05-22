"""Centralized bot message templates for consistent UX tone."""

WELCOME_TEXT = "👋 <b>DASTYOR AI</b>"

CV_INSTRUCTION_TEXT = (
    "📄 <b>CV</b>\n"
    "Formani to‘ldiring → to‘lov (5 000 so‘m) → PDF botga."
)

CV_INTRO_TEXT = ""

OBY_INTRO_TEXT = ""

OBY_INSTRUCTION_TEXT = (
    "✍️ <b>Obyektivka</b>\n"
    "Forma yoki ovoz → to‘lov → Word botga.\n\n"
    "🎙 Pastda <b>namuna ovoz</b> keladi — tinglab, shu tartibda o‘zingiz ovoz yuboring.\n"
    "F.I.Sh., tug‘ilgan sana/joy, ta’lim, ish, oila."
)

OBY_AUDIO_WAIT_HINT = (
    "🎙 Ovoz yuboring yoki ✍️ <b>Obyektivka</b> tugmasi — forma.\n"
    "Bekor: <b>bekor</b> yoki 🔙 <b>Orqaga</b>."
)

HELP_TEXT = (
    "ℹ️ <b>Yordam — DASTYOR AI</b>\n\n"
    "<b>Bot nima qiladi?</b>\n"
    "CV (PDF) va Obyektivka (Word) tayyorlaydi. "
    "Tayyor fayl shu Telegram chatiga keladi.\n\n"
    "📄 <b>CV</b>\n"
    "• <b>CV Resume</b> tugmasi → forma ochiladi\n"
    "• Ma’lumotlarni to‘ldiring\n"
    "• <b>5 000 so‘m</b> — ko‘rsatilgan kartaga o‘tkazing, skrinshot yuboring\n"
    "• Admin tasdiqlagach formada <b>PDF botga yuborish</b> — fayl shu yerga\n\n"
    "✍️ <b>Obyektivka</b>\n"
    "• <b>Obyektivka</b> tugmasi → forma yoki ovoz\n"
    "• Ovozda: F.I.Sh., tug‘ilgan sana/joy, ta’lim, ish, oila\n"
    "• To‘lov CV bilan bir xil (5 000 so‘m + skrinshot)\n"
    "• Tasdiqdan keyin <b>Word botga yuborish</b> — .docx shu yerga\n\n"
    "<b>Buyruqlar</b>\n"
    "/start — bosh menyu\n"
    "/docs — to‘lov holati\n"
    "/contact — savol yoki muammo\n"
    "/help — yordam\n\n"
    "🔙 <b>Orqaga</b> — menyuga qaytish."
)

SUPPORT_START_TEXT = (
    "📩 <b>Murojaat</b>\n\n"
    "Muammo yoki savol — matn, rasm yoki fayl.\n"
    "Bekor: <b>bekor</b>"
)

SUPPORT_SUCCESS_TEXT = "✅ Yuborildi. Javob kuting."

SUPPORT_INVALID_TEXT = "⚠️ Matn, rasm yoki fayl yuboring. Bekor: <b>bekor</b>"

SUPPORT_CANCEL_TEXT = "↩️ Bekor. Menyu pastda."

UNKNOWN_INPUT_TEXT = "Tugma tanlang yoki /start"

ADMIN_PANEL_OPENED_TEXT = "🛠 <b>Admin panel</b>"

ADMIN_ONLY_TEXT = "⛔ Faqat adminlar uchun."

ADMIN_STATUS_TEXT = "✅ Bot ishlayapti."
