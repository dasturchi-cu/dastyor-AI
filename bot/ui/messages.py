"""Centralized bot message templates for consistent UX tone."""

WELCOME_TEXT = (
    "👋 <b>DASTYOR AI</b> ga xush kelibsiz!\n\n"
    "<b>Bot nima qiladi?</b>\n"
    "CV va Obyektivka tayyorlaydi — tayyor fayl shu chatga keladi.\n\n"
    "📄 <b>CV Resume</b> — forma → ko‘rish → 5 000 so‘m → <b>PDF</b>\n"
    "✍️ <b>Obyektivka</b> — forma yoki ovoz → <b>demo ko‘rish</b> → 5 000 so‘m → <b>Word</b>\n\n"
    "🔍 To‘lovdan oldin <b>demo versiya</b>ni ko‘rib, sifatni tekshirishingiz mumkin.\n"
    "💳 To‘lov: kartaga o‘tkazma + skrinshot. Admin tasdiqlagach hujjatni yuborasiz.\n\n"
    "👇 Pastdagi tugmalardan xizmatni tanlang.\n"
    "ℹ️ <b>Yordam</b> · 🆘 <b>Murojaat</b> · 🔙 <b>Orqaga</b>"
)

CV_INSTRUCTION_TEXT = (
    "📄 <b>CV</b>\n"
    "Formani to‘ldiring → to‘lov (5 000 so‘m) → PDF botga."
)

CV_INTRO_TEXT = ""

OBY_INTRO_TEXT = ""

OBY_INSTRUCTION_TEXT = (
    "✍️ <b>Obyektivka</b>\n"
    "Forma yoki ovoz → <b>demo ko‘rish</b> → to‘lov (5 000 so‘m) → Word botga.\n\n"
    "🔍 To‘lovdan oldin <b>DEMO VERSIYA</b>ni ko‘rib, sifatni tekshirishingiz mumkin.\n\n"
    "📌 Obyektivka tayyorlash uchun quyidagi ma’lumotlarni <b>audiodagi kabi</b> o‘qib jo‘nating:\n\n"
    "1. F.I.Sh. (Familiyasi, ismi, sharifi)\n"
    "2. Tug‘ilgan yili, oyi, sanasi\n"
    "3. Tug‘ilgan joyi (viloyat, tuman/shahar)\n"
    "4. Millati\n"
    "5. Ma’lumoti\n"
    "6. Tamomlagan o‘quv yurti (nomi va yili)\n"
    "7. Mutaxassisligi (diplom bo‘yicha)\n"
    "8. Partiyaviyligi\n"
    "9. Ilmiy darajasi\n"
    "10. Ilmiy unvoni\n"
    "11. Qaysi chet tillarini biladi\n"
    "12. Davlat mukofotlari bilan taqdirlanganligi\n"
    "13. Deputatlar kengashi a’zoligi (ha/yo‘q, qaysi kengash)\n"
    "14. Mehnat faoliyati (qayerda, qaysi lavozimda, boshlagan va tugatgan sanalari bilan)\n"
    "15. Rasm elektron variantda\n\n"
    "👨‍👩‍👧‍👦 <b>Oila a’zolari</b> (ota, ona, aka, uka, opa, singil, turmush o‘rtog‘i) — har biri uchun:\n"
    "• F.I.Sh.\n"
    "• Tug‘ilgan yili va joyi\n"
    "• Ish joyi va lavozimi\n"
    "• Yashash manzili\n\n"
    "🎙 Pastda <b>namuna ovoz</b> keladi — tinglab, xuddi shunday o‘qing."
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
    "🆘 <b>Murojaat</b> — matn, ovozli xabar, rasm yoki fayl\n\n"
    "<b>Buyruqlar</b>\n"
    "/start — bosh menyu\n"
    "/docs — to‘lov holati\n"
    "/contact — murojaat\n"
    "/help — yordam\n\n"
    "🔙 <b>Orqaga</b> — menyuga qaytish."
)

SUPPORT_START_TEXT = (
    "📩 <b>Murojaat</b>\n\n"
    "Savolingiz yoki muammoingizni yuboring — admin tez orada javob beradi.\n\n"
    "<b>Yuborishingiz mumkin:</b>\n"
    "📝 Matn\n"
    "🎙 Ovozli xabar\n"
    "🖼 Rasm (skrinshot ham bo‘ladi)\n"
    "📎 Fayl (PDF, Word va hokazo)\n\n"
    "Bekor: <b>bekor</b> yozing yoki 🔙 <b>Orqaga</b> tugmasi."
)

SUPPORT_SUCCESS_TEXT = "✅ Yuborildi. Javob kuting."

SUPPORT_INVALID_TEXT = (
    "⚠️ Matn, ovozli xabar, rasm yoki fayl yuboring.\n"
    "Bekor: <b>bekor</b>"
)

SUPPORT_CANCEL_TEXT = "↩️ Bekor. Menyu pastda."

UNKNOWN_INPUT_TEXT = "Tugma tanlang yoki /start"

ADMIN_PANEL_OPENED_TEXT = "🛠 <b>Admin panel</b>"

# Admin broadcast: /broadcast tayyor
BROADCAST_FIX_ANNOUNCEMENT = (
    "✅ <b>DASTYOR AI yangilandi</b>\n\n"
    "Botdagi asosiy xatolar tuzatildi.\n"
    "CV, Obyektivka, to‘lov va Murojaat ishlaydi.\n\n"
    "/start — menyu · 🆘 Murojaat — savol"
)

ADMIN_ONLY_TEXT = "⛔ Faqat adminlar uchun."

ADMIN_STATUS_TEXT = "✅ Bot ishlayapti."
