"""Centralized bot message templates for consistent UX tone."""

WELCOME_TEXT = (
    "👋 <b>DASTYOR AI</b>\n\n"
    "Rezyume va ma’lumotnoma tayyorlash — tez va tartibli.\n\n"
    "📄 <b>CV Resume</b> — PDF (5 000 so‘m, 1 marta)\n"
    "✍️ <b>Obyektivka</b> — Word (ovoz yoki qo‘lda)\n"
    "📂 <b>Mening hujjatlarim</b> — to‘lov holati\n"
    "🆘 <b>Murojaat</b> · ℹ️ <b>Yordam</b>\n\n"
    "Tugmani bosing — avval yo‘riqnoma, keyin forma."
)

CV_INSTRUCTION_TEXT = (
    "📌 <b>CV uchun tayyorlang:</b>\n"
    "ism, kasb, telefon, rasm, ta’lim, ish tajribasi, tillar, ko‘nikmalar.\n\n"
    "Formada <b>jonli ko‘rinish</b> bor — har qadamda tekshirasiz."
)

CV_INTRO_TEXT = (
    "📄 <b>CV — 4 qadam</b>\n\n"
    "1️⃣ Pastdagi tugma → forma\n"
    "2️⃣ Ma’lumotlarni to‘ldiring\n"
    "3️⃣ Ko‘rinishni tekshiring\n"
    "4️⃣ <b>5 000 so‘m</b> → admin tasdiqlash → <b>1 ta PDF</b> botga\n\n"
    "💡 To‘ldirish bepul; PDF yuborish — bir marta."
)

OBY_INTRO_TEXT = (
    "✍️ <b>Obyektivka — 4 qadam</b>\n\n"
    "1️⃣ Namuna ovozni tinglang\n"
    "2️⃣ Xuddi shunday <b>ovoz</b> yuboring yoki formani oching\n"
    "3️⃣ Word ni ko‘rib chiqing\n"
    "4️⃣ <b>5 000 so‘m</b> → admin → <b>1 ta Word</b> botga\n\n"
    "💡 Ovoz va forma bepul; Word yuborish — bir marta."
)

OBY_INSTRUCTION_TEXT = (
    "📌 <b>Ovozda quyidagilarni o‘qing</b> (namunadagi tartibda):\n"
    "F.I.Sh., tug‘ilgan sana/joy, millat, ta’lim, OTM, mutaxassislik, "
    "ish joylari, oila a’zolari (ism, tug‘ilgan, ish, manzil).\n\n"
    "🎙 Tayyor bo‘lsa — ovozli xabar yuboring (namuna audio ixtiyoriy)."
)

OBY_AUDIO_WAIT_HINT = (
    "🎙 <b>Obyektivka rejimi</b>\n\n"
    "Ovozli xabar yuboring (namunadagi kabi).\n"
    "Yoki ✍️ <b>Obyektivka</b> tugmasini qayta bosing — forma ochiladi.\n\n"
    "Bekor: <b>bekor</b> yozing yoki 🔙 <b>Orqaga</b>."
)

HELP_TEXT = (
    "ℹ️ <b>Yordam</b>\n\n"
    "📄 <b>CV</b> — tugma → forma → 5 000 so‘m → PDF\n"
    "✍️ <b>Obyektivka</b> — ovoz yoki forma → Word\n"
    "📂 <b>Mening hujjatlarim</b> (/docs) — holat\n"
    "🆘 <b>Murojaat</b> — muammo, to‘lov\n\n"
    "Menyu: /start yoki 🔙 <b>Orqaga</b>"
)

SUPPORT_START_TEXT = (
    "📩 <b>Murojaat</b>\n\n"
    "Matn, rasm, ovoz yoki fayl yuboring.\n"
    "Muammoni qisqa yozing (masalan: to‘lov, forma ochilmayapti).\n\n"
    "Bekor: <b>bekor</b> yozing."
)

SUPPORT_SUCCESS_TEXT = (
    "✅ Qabul qilindi. Admin tez orada javob beradi.\n\n"
    "Davom etish uchun pastdagi menyudan xizmat tanlang."
)

SUPPORT_INVALID_TEXT = (
    "⚠️ Qabul qilinmadi.\n"
    "Matn, rasm, ovoz yoki fayl yuboring — yoki <b>bekor</b> yozing."
)

SUPPORT_CANCEL_TEXT = "↩️ Bekor qilindi. Asosiy menyu pastda."

UNKNOWN_INPUT_TEXT = (
    "Menyudan tanlang:\n"
    "📄 CV  •  ✍️ Obyektivka  •  📂 Hujjatlar  •  🆘 Murojaat\n\n"
    "Yoki /start"
)

ADMIN_PANEL_OPENED_TEXT = "🛠 <b>Admin panel</b>\nBo‘limni tanlang."

ADMIN_ONLY_TEXT = "⛔ Faqat adminlar uchun."

ADMIN_STATUS_TEXT = "✅ Bot ishlayapti."  # legacy; main.py uses format_admin_stats_text
