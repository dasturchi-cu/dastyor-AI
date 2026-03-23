# Loyiha Xarajat Hisobi (1000 User / 1 Oy)

## 1) Hozir nimalarga pul ketadi

Quyidagi komponentlar loyihada real ishlatilmoqda:

- Server (FastAPI + bot + OCR worker) — doimiy compute xarajati.
- Redis/Celery (agar async job yoqilgan bo'lsa) — qo'shimcha compute yoki managed Redis.
- Supabase (users, subscriptions, payments, usage buckets) — DB/storage xarajati.
- Google Gemini API (OCR, tarjima, STT, AI funksiyalar) — token/so'rov bo'yicha xarajat.
- Playwright/WeasyPrint bilan PDF render — asosan compute (API narxi emas).
- Domain/SSL/CDN (agar alohida ishlatilsa) — infra qo'shimcha.

Telegram API o'zi odatda bepul (bot message/doc yuborish uchun Telegramdan billing bo'lmaydi).

---

## 2) Koddan ko'rinayotgan texnologiyalar (xarajatga ta'sir qiladiganlar)

- AI/Gemini ishlatiladi:

```23:41:bot/services/ai_service.py
import google.generativeai as genai
...
GEMINI_MODELS = [
    'gemini-2.5-flash',
    'gemini-2.0-flash',
    'gemini-1.5-flash-latest',
]
```

- OCR va worker stack:

```21:27:docker-compose.yml
- PADDLE_OCR_LANG=en
- PADDLE_OCR_MAX_SIDE=1800
- PADDLE_OCR_DET_LIMIT_SIDE_LEN=1800
...
worker:
  command: ["celery", "-A", "backend.celery_app.celery_app", "worker", "--loglevel=INFO", "--concurrency=1"]
```

- Supabase quota/subscription hisob:

```420:452:bot/services/supabase_db.py
def db_service_bucket_get_many(user_id: int, bucket_keys: list[str]) -> dict[str, int]:
    ...
    c.table("service_usage_buckets")
```

---

## 3) 1000 user uchun oylik taxmin (USD)

Quyidagi hisob **taxminiy**. Aniq summa sizning real trafik va model token sarfiga bog'liq.

### Asosiy taxminlar

- 1000 registratsiya user.
- 30% MAU (oyiga faol): 300 user.
- O'rtacha 1 faol user oyiga 40 ta amaliy so'rov (OCR/translate/cv/STT aralash).
- Jami ~12,000 AI-ishlovli so'rov/oy.

### A) Minimal (yengil traffic)

- Server (1 API + 1 worker kichik plan): **$25–45**
- Supabase (Pro yoki o'xshash): **$25**
- Gemini API (past token sarf): **$20–60**
- Redis/qo'shimcha xizmatlar: **$0–15**

**Jami: ~$70–145 / oy**

### B) O'rtacha (real biznes yuklama)

- Server (barqaror 2 service + worker): **$50–120**
- Supabase: **$25–60**
- Gemini API (o'rtacha token): **$80–250**
- Redis/monitoring/log: **$10–40**

**Jami: ~$165–470 / oy**

### C) Yuqori (og'ir OCR/AI ishlatish)

- Server (CPU/RAM ko'proq): **$120–280**
- Supabase (storage/egress oshgan): **$60–120**
- Gemini API (token yuqori): **$300–1000+**
- Redis + qo'shimcha infra: **$30–80**

**Jami: ~$510–1480+ / oy**

---

## 4) Tez formula (o'zingiz uchun)

Oylik xarajat:

`Total = Infra + Supabase + Gemini + Redis/Other`

Gemini qismi:

`Gemini = (oylik input token / 1M * input narx) + (oylik output token / 1M * output narx)`

Yoki soddaroq:

`Gemini ~= (so'rovlar soni * 1 ta so'rovning o'rtacha AI xarajati)`

---

## 5) Sizning loyiha uchun tez xulosa

- Hozir eng katta risk xarajat: **Gemini API** va **compute (OCR/PDF render)**.
- Supabase odatda barqaror ikkinchi xarajat.
- 1000 user uchun amalda ko'p loyiha **$150–500/oy** diapazonda yuradi (o'rtacha trafikda).
- Agar OCR/STT juda ko'p ishlatilsa, xarajat tez **$700+** ga chiqadi.

---

## 6) Xarajatni tushirish bo'yicha amaliy yo'llar

- OCR va tarjimada oldin local/Paddle, keyin Gemini fallback (sizda qisman bor).
- WebP/JPG siqish, image side limit (token va compute kamayadi).
- Cache: bir xil faylga qayta OCR bo'lmasin.
- Premium limitlarni qat'iy ushlash (sizda quota bucket bor).
- Og'ir renderlarni queue qilib pik vaqtni tekislash.

---

## 7) Agar xohlasangiz keyingi qadam

Men sizga keyingi bosqichda **real kalkulyator jadval** ham chiqarib beraman:

- Free / Standard / Premium user ulushi
- har tarif bo'yicha o'rtacha usage
- shundan aniqroq oylik P&L (daromad-xarajat) modeli.
