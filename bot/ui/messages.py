"""Centralized bot message templates for consistent UX tone."""

WELCOME_TEXT = (
    "👋 <b>DASTYOR AI</b>\n\n"
    "Quyidagi tugmalardan birini tanlang — avval qisqa yo‘riqnoma, "
    "keyin forma ochiladi:\n\n"
    "📄 <b>CV Resume</b> — rezyume tayyorlash\n"
    "✍️ <b>Obyektivka</b> — ma’lumotnoma (ovoz yoki qo‘lda)\n"
    "🆘 <b>Murojaat</b> — admin bilan bog‘lanish\n"
    "ℹ️ <b>Yordam</b> — qisqa ko‘rsatma"
)

CV_INTRO_TEXT = (
    "📄 <b>CV (rezyume) — qanday ishlaydi?</b>\n\n"
    "1️⃣ <b>Formani oching</b> — pastdagi ko‘k tugma\n"
    "2️⃣ Ma’lumotlaringizni to‘ldiring (tajriba, ta’lim, foto)\n"
    "3️⃣ Jonli ko‘rinishda tekshiring\n"
    "4️⃣ <b>5 000 so‘m</b> to‘lov → admin tasdiqlash → <b>1 ta PDF</b> botga yuboriladi\n\n"
    "💡 Formani bepul to‘ldirasiz; <b>botga PDF yuborish</b> — bir martalik to‘lov."
)

OBY_INTRO_TEXT = (
    "✍️ <b>Obyektivka (ma’lumotnoma) — qanday ishlaydi?</b>\n\n"
    "1️⃣ <b>Quyidagi namuna ovozni</b> tinglang (qanday o‘qish kerakligi)\n"
    "2️⃣ Xohlasangiz shu yerga <b>ovozli xabar</b> yuboring — bot maydonlarni to‘ldiradi\n"
    "3️⃣ Yoki pastdagi tugma orqali <b>formani ochib</b> qo‘lda kiriting\n"
    "4️⃣ Tayyor Word ni ko‘ring → <b>5 000 so‘m</b> → admin tasdiqlash → <b>1 ta Word</b> botga\n\n"
    "💡 Ovozli to‘ldirish <b>bepul</b>; <b>botga Word yuborish</b> — bir martalik to‘lov."
)

OBY_INSTRUCTION_TEXT = (
    "📌 <b>Obyektivka tayyorlash uchun quyidagi ma’lumotlarni audiodagi kabi o‘qib jo‘nating:</b>\n\n"
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
    "👨‍👩‍👧‍👦 <b>Oila a’zolari haqida ma’lumot:</b>\n"
    "(Ota, ona, aka, uka, opa, singil, turmush o‘rtog‘i)\n\n"
    "Har biri uchun quyidagilar ko‘rsatiladi:\n"
    "1. F.I.Sh.\n"
    "2. Tug‘ilgan yili va joyi\n"
    "3. Ish joyi va lavozimi\n"
    "4. Yashash manzili\n\n"
    "🎙 <b>Quyidagi audio namunaga o‘xshab o‘qib yuboring:</b>"
)

HELP_TEXT = (
    "ℹ️ <b>Yordam</b>\n\n"
    "📄 <b>CV</b> — tugmani bosing → yo‘riqnoma → «Formani ochish»\n"
    "✍️ <b>Obyektivka</b> — namuna ovoz + forma yoki ovoz yuborish\n"
    "🆘 <b>Murojaat</b> — muammo bo‘lsa matn/rasm/ovoz yuboring\n\n"
    "Asosiy menyuga: <b>Orqaga</b> yoki /start"
)

SUPPORT_START_TEXT = (
    "📩 <b>Murojaat yuborish</b>\n\n"
    "Yuborishingiz mumkin:\n"
    "• Matn\n"
    "• Rasm\n"
    "• Ovozli xabar\n"
    "• Fayl\n\n"
    "Muammoni aniq yozing — admin javob beradi."
)

SUPPORT_SUCCESS_TEXT = (
    "✅ Murojaatingiz qabul qilindi.\n"
    "Admin tez orada javob beradi.\n\n"
    "Yangi xizmat uchun /start bosing."
)

SUPPORT_INVALID_TEXT = (
    "⚠️ Bu format qabul qilinmadi.\n"
    "Matn, rasm, ovoz yoki fayl yuboring."
)

SUPPORT_CANCEL_TEXT = "↩️ Murojaat rejimi yopildi."

UNKNOWN_INPUT_TEXT = (
    "🤖 Tushunmadim.\n\n"
    "Quyidagilardan birini tanlang:\n"
    "📄 CV  •  ✍️ Obyektivka  •  🆘 Murojaat  •  ℹ️ Yordam"
)

ADMIN_PANEL_OPENED_TEXT = (
    "🛠 Admin panel ochildi.\n"
    "Kerakli bo'limni tanlang."
)

ADMIN_ONLY_TEXT = "⛔ Bu bo'lim faqat adminlar uchun."

ADMIN_STATUS_TEXT = "✅ Bot holati: barqaror va ishchi."
