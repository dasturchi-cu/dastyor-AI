LASHBOT — AI HUJJAT SERVIS TELEGRAM BOT
TEXNIK TOPSHIRIQ (FULL TZ)
1. Umumiy tavsif
Telegram bot va Web App asosidagi AI hujjat servis platforma. Bot orqali foydalanuvchi turli hujjat tayyorlash, OCR, tarjima, transliteratsiya va imlo tekshirish xizmatlaridan foydalanadi. Tizim AI, OCR va document-processing texnologiyalariga asoslanadi.
2. Start menyu tugmalari
Bot ochilganda quyidagi grid menyu chiqadi:
- Obyektivka AI
- Rasm → Word AI
- Krill-Lotin
- Tarjima fayl
- Rasm → PDF
- Imlo tekshirishd
- Premium xizmatlar
- Balans
- Aloqa uchun
3. Obyektivka AI moduli
Jarayon:
1) Tugma bosilganda namuna obyektivka shablon matni ko‘rsatiladi. Foydalanuvchi matndan o‘z malumotlarini qanday tartibda aytishini xayolan ko‘rib oladi. 
2) so‘ng Audio yuborish tugmasi bosib, o‘z malumotlarini birma bir o‘qib beradi
3) Foydalanuvchi audio yuboradi
4) Speech-to-Text orqali matnga o‘tkaziladi
5) AI ma’lumotlarni ajratadi (FIO, tug‘ilgan yil, manzil, ta’lim, tajriba, ko‘nikma)
6) Shablon avtomatik to‘ldiriladi
7) Mini appda preview ko‘rsatiladi, xatolik bo‘lsa klaviaturada yozib to‘g‘irlaydi
8) Output: DOCX va PDF
4. Rasm → Word AI moduli
Foydalanuvchi rasm(lar) yuboradi. OCR va layout-restore ishlaydi.
Saqlanishi shart: shrift, jadval, ustun, satr, joylashuv.
Jarayon vaqtida progress xabari chiqadi (10–20 sekund kuting).
Output: DOCX (1:1 ko‘rinish).
5. Kirill ↔ Lotin moduli
Tugma bosilganda tanlov chiqadi:
Grid ko‘rinishida (yonma yon) 2 ta tugma chiqadi
- Kirill → Lotin
- Lotin → Kirill
Qabul qilinadi: matn, DOCX, PPTX, XLSX.
O‘zbek alifbo qoidalari asosida transliteratsiya qilinadi.
6. Tarjima fayl moduli
Til tanlash grid menyu:
- O‘zbek → Ingliz
- Ingliz → O‘zbek
- Rus → O‘zbek
- O‘zbek → Rus
- Rus → Ingliz
Keyin DOC/PPT/XLS fayl yuboriladi.
AI tarjima qiladi, struktura saqlanadi.
Output: original formatda.
7. Rasm → PDF moduli
Bot rasmlarni qabul qiladi (2–20 dona).
Foydalanuvchi 'Tayyor' tugmasini bosadi.
Tizim rasmlarni tartib bilan birlashtirib PDF yaratadi.
Output: bitta PDF fayl.
8. Imlo tekshirish moduli
Foydalanuvchi DOC yoki PPT fayl yuboradi.
AI imlo xatolarini aniqlaydi.
Tuzatilgan fayl va xatolar ro‘yxati qaytariladi.
9. Premium xizmatlar
Tugma bosilganda Web App ochiladi.
Ichida grid advanced servislar:
- Obyektivka AI Pro
- Rasm → Word Pro
- Modern CV builder
-(4-knopka xozircha bo‘sh)
Premium — pullik model.
10. Balans moduli
Ko‘rsatadi: joriy balans, kreditlar, tarif.
To‘ldirish: Click, Payme, Uzkard, Humo
11. Aloqa moduli
Admin kontaktlari, support chat, murojaat yuborish.
12. Texnik stack
Backend: Python FastAPI yoki Node.js
Database: PostgreSQL
Queue: Redis
AI: LLM + Speech-to-Text
OCR: professional OCR engine
Frontend: Telegram Bot API + WebApp React
13. Queue va vaqt boshqaruvi
Og‘ir vazifalar job-queue orqali bajariladi.
Progress status ko‘rsatiladi.
Timeout nazorati mavjud.
14. Xatolik holatlari
OCR aniqlamadi — qayta yuklash so‘raladi.
Audio tushunilmadi — qayta yozish.
Noto‘g‘ri format — ogohlantirish xabari.
