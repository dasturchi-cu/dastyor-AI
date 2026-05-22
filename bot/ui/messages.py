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
    "3️⃣ Tayyor PDF/Word ni ko‘rib chiqing\n"
    "4️⃣ Kerak bo‘lsa <b>5 000 so‘m</b> to‘lov → admin tasdiqlash → fayl botga keladi\n\n"
    "💡 Formani bepul ko‘rishingiz mumkin; yuklab olish/to‘lov alohida."
)

OBY_INTRO_TEXT = (
    "✍️ <b>Obyektivka (ma’lumotnoma) — qanday ishlaydi?</b>\n\n"
    "1️⃣ <b>Quyidagi namuna ovozni</b> tinglang (qanday o‘qish kerakligi)\n"
    "2️⃣ Xohlasangiz shu yerga <b>ovozli xabar</b> yuboring — bot maydonlarni to‘ldiradi\n"
    "3️⃣ Yoki pastdagi tugma orqali <b>formani ochib</b> qo‘lda kiriting\n"
    "4️⃣ Tayyor Word ni ko‘ring → <b>5 000 so‘m</b> to‘lov → admin tasdiqlash → botga yuboriladi\n\n"
    "💡 Ovozli to‘ldirish <b>bepul</b>; faqat tayyor hujjat yuborish pullik."
)

OBY_SAMPLE_TEXT = (
    "📌 <b>Ovozda aytish kerak bo‘lganlar (qisqa ro‘yxat):</b>\n\n"
    "• F.I.Sh., tug‘ilgan sana va joyi, millati\n"
    "• Ma’lumot, o‘quv yurti, mutaxassislik\n"
    "• Partiyaviylik, ilmiy daraja/unvon, tillar\n"
    "• Mukofotlar, deputatlik (agar bor bo‘lsa)\n"
    "• <b>Ish joylari</b> — tashkilot, lavozim, boshlanish/tugash yillari\n"
    "• <b>Oila a’zolari</b> — har biri: F.I.Sh., tug‘ilgan yili/joyi, ish joyi, manzil\n\n"
    "🎙 Keyingi xabarda <b>namuna ovoz</b> keladi — shu tartibda o‘qing."
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
