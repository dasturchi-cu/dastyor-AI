# Dastyor AI — Supabase Integratsiya (Bot)

## 1) Kerakli `.env` qiymatlar
Supabase bilan ishlash uchun backend (bot + FastAPI) quyidagilarni `.env`dan o‘qiydi:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY` (fallback)
- `SUPABASE_SERVICE_ROLE_KEY` (tavsiya qilinadi, RLS yozish uchun)
- `PREMIUM_ADMIN_GROUP_ID` (Telegram admin guruh ID)

`supabase_db.py` server-side yozish uchun `SUPABASE_SERVICE_ROLE_KEY` bo‘lsa shuni ishlatadi, bo‘lmasa `SUPABASE_ANON_KEY`ga tushadi.

## 2) Supabase’da yaratilgan jadval/larg’ining vazifasi

Quyidagi jadval/kolonkalar sizning loyihangizdagi oqimlarga mos:

### `users`
- Maqsad: Telegram user profilini saqlash.
- Bot ishlatadi: `bot/services/user_service.py` orqali (`db_get_user`, `db_upsert_user`).
- Muhim ustunlar:
  - `id` (telegram_id bilan moslik)
  - `telegram_id`, `username`, `first_name`, `created_at`
  - `last_active`, `files_processed`, `sessions`, `is_banned` (bot logika uchun)

### `premium_subscriptions`
- Maqsad: premium aktiv davrlar (standard/premium).
- Bot ishlatadi:
  - `bot/services/settings_service.py -> is_premium()`
  - `bot/services/supabase_db.py -> db_is_premium()`
- Qanday tekshiradi:
  - `end_date` bo‘lsa `end_date >= now()`
  - bo‘lmasa `expire_date >= now()`
- Admin tasdiqdan keyin bu jadvalga premium aktiv kiritiladi.

### `payments`
- Maqsad: foydalanuvchi to‘lov “request”lari (pending/approved/rejected).
- Bot ishlatadi:
  - WebApp’dan `POST /api/premium_receipt` kelganda `payments`ga `pending` yoziladi
  - Admin tasdiqda `payments.status` yangilanadi (`approved` yoki `rejected`)

### `bot_settings`
- Maqsad: global sozlamalar.
- Bot ishlatadi:
  - `daily_limit` (kunlik bepul limit)
  - `maintenance_mode` (texnik ishlar rejimi)

### `daily_usage`
- Maqsad: har kunlik limit (free tier) uchun counter.
- Bot ishlatadi:
  - `bot/services/usage_tracker.py` orqali
  - `supabase_db.py -> db_get_usage`, `db_increment_usage`

### `generated_files`
- Maqsad: foydalanuvchiga yuborilgan fayllar (DOCX/PDF/TXT va h.k.) izlari.
- Hozir holat: schema bor, lekin bot kodida “sertifikat” darajasida yozish/UX uchun to‘liq ulanmagan.

### `ocr_logs`
- Maqsad: OCR jarayonlari loglari.
- Hozir holat: schema bor, lekin botda end-to-end yozish to‘liq integratsiya qilinmagan.

### `cv_generations`
- Maqsad: CV generatsiya loglari.
- Hozir holat: schema bor, lekin botda to‘liq yozish integratsiya qilinmagan.

### `objective_generations`
- Maqsad: obyektivka generatsiya loglari.
- Hozir holat: schema bor, lekin botda to‘liq yozish integratsiya qilinmagan.

### `support_messages`
- Maqsad: support so‘rovlar / admin javoblari izlari.
- Hozir holat: schema bor, lekin hozir bot `bot/services/support_service.py` ichida JSON fayl bilan ishlayapti. (To‘liq Supabase’ga ko‘chirilmagan.)

### `usage_logs`
- Maqsad: feature ishlatilish audit loglari (OCR/CV/spellcheck/translate).
- Hozir holat: schema bor, lekin hozir botda to‘liq yozish integratsiya qilinmagan.

## 3) Premium webapp flow (end-to-end)

1. User webappda `Standart sotib olish` yoki `Premium sotib olish` bosadi.
2. `premium.html` chek screenshot’ini yuklaydi va:
   - `POST /api/premium_receipt` ga `plan` va rasm yuboradi.
3. Server:
   - `payments` jadvaliga `pending` payment row yaratadi (agar Supabase ishlayotgan bo‘lsa)
   - admin guruhga rasm + `✅ Tasdiqlash` / `❌ Rad etish` tugmalarini yuboradi
4. Admin tugma bosadi:
   - `prempay_approve_<id>` yoki `prempay_reject_<id>` callback keladi
5. Callback handler:
   - agar `<id>` Supabase `payments.id` bo‘lsa `payments.status` yangilanadi
   - approved bo‘lsa `premium_subscriptions`ga:
     - `standard` -> 7 kun
     - `premium` -> 30 kun
   - userga xabar yuboriladi:
     - `✅ Premium tarifingiz faollashtirildi`
     - yoki `❌ To'lov tasdiqlanmadi`

## 4) Maintenance mode

- Admin komandalar:
  - `/maintenance_on` — maintenance yoqish
  - `/maintenance_off` — maintenance o‘chirish
  - `/maintenance_status` — holatni ko‘rish
- Maintenance yoqilganda:
  - admin bo‘lmagan userlar bloklanadi
  - adminlar ishlashda davom etadi

## 5) Supabase’da tezkor tekshiruv (SQL)

Quyidagilarni Supabase SQL Editor’da ishlating:

```sql
select count(*) from public.users;
select count(*) from public.payments;
select count(*) from public.premium_subscriptions;
select * from public.bot_settings limit 1;

select * from public.v_active_premium limit 5;
```

## 6) Eslatma

Agar Supabase’da RLS yoqilgan bo‘lsa va `SUPABASE_SERVICE_ROLE_KEY` berilmasa, bot yozolmay qolishi mumkin. Shuning uchun `SUPABASE_SERVICE_ROLE_KEY` tavsiya qilinadi.

