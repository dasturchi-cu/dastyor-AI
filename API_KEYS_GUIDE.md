# 🔑 API KALITLARNI OLISH QO'LLANMASI (GUIDE)

Ushbu qo'llanma orqali siz **LASHBOT** to'liq ishlashi uchun kerakli barcha kalitlarni qayerdan va qanday olishni o'rganasiz.

---

## 1. OPENAI API KEY (Miya 🧠)
**Nimaga kerak?**
- Audio xabarlarni matnga aylantirish (Speech-to-Text).
- Matndan ma'lumotlarni ajratib olish (GPT-3.5/4).
- Tarjima va imlo tekshirish.

**Qanday olinadi?**
1. **Saytga kiring:** [platform.openai.com](https://platform.openai.com)
2. **Ro'yxatdan o'ting:** "Sign Up" tugmasini bosing (Email yoki Google akkaunt orqali).
3. **API bo'limiga o'ting:** Chap menyudan **"API Keys"** tugmasini bosing (yoki [bu havola](https://platform.openai.com/api-keys) orqali).
4. **Yangi kalit yaratish:**
   - **"+ Create new secret key"** tugmasini bosing.
   - Nomiga `Lashbot` deb yozing.
   - "Create secret key" ni bosing.
5. **Nusxalab oling:** `sk-proj-...` bilan boshlanadigan uzun kod chiqadi. Uni nusxalab oling va hech kimga ko'rsatmang!
   - *Eslatma:* Bu kalit faqat bir marta ko'rinadi.
6. **Balansni to'ldirish:** OpenAI pullik xizmat (juda arzon, lekin tekin emas). [Billing](https://platform.openai.com/settings/organization/billing/overview) bo'limida kamida $5 (5 dollar) to'ldirishingiz kerak bo'ladi.

---

## 2. TELEGRAM BOT TOKEN (Bot tanasi 🤖)
**Nimaga kerak?**
- Botni Telegramda ishlatish uchun.

**Qanday olinadi?**
1. Telegramda **[@BotFather](https://t.me/BotFather)** ga kiring.
2. `/newbot` buyrug'ini yozing.
3. Botga nom bering (Masalan: `Hujjatchi AI`).
4. Botga username bering (oxiri `bot` bilan tugashi shart, masalan `lash_hujjat_bot`).
5. **Tokenni oling:** BotFather sizga uzun kod beradi (`123456789:AAVg...`). Shuni nusxalab oling.

---

## 3. GOOGLE CLOUD VISION API (Ko'z 👁️ - Kelajak uchun)
**Nimaga kerak?**
- Rasmdagi matnlarni o'qish (OCR) uchun eng kuchli vosita.

**Qanday olinadi?**
1. **Saytga kiring:** [console.cloud.google.com](https://console.cloud.google.com/)
2. **Loyiha yarating:** "New Project".
3. **API yoqing:** "Library" bo'limidan "Cloud Vision API" deb qidiring va "Enable" bosing.
4. **Kalit oling:** "Credentials" -> "Create Credentials" -> "API Key".
5. Bu kalitni nusxalab oling.

---

## 🛠 KALITLARNI QAYERGA QO'YISH KERAK?

Loyihangizdagi `.env` faylini oching va kalitlarni quyidagicha joylashtiring:

```ini
# Telegram Bot Tokeningiz (BotFather'dan)
BOT_TOKEN=8378958011:AAGsCLzuZDug9yLJLQHzJ9y0xygYsghGDLw

# OpenAI Kaliti (sk-proj-... bilan boshlanadi)
OPENAI_API_KEY=sk-proj-SizningHaqiqiyKalitingizShuYerga

# Admin ID (Sizning Telegram ID raqamingiz)
ADMIN_USER_ID=12345678
```

⚠️ **DIQQAT:** Faylni saqlashni unutmang (Ctrl+S)!
