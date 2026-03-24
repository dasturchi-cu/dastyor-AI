-- =============================================================================
-- Supabase → SQL Editor: bitta marta ishga tushiring (yoki yangi qatorlarni qo‘shing).
-- Maqsad: bot / Web API tez-tez qiladigan .eq() filtrlari uchun indeks.
--
-- Eslatma: users.id odatda PRIMARY KEY — u allaqachon indekslangan.
-- telegram_id bo‘yicha alohida qidiruv bo‘lsa (yoki id dan farq qilsa) quyidagi indeks foydali.
-- daily_usage: UNIQUE (user_id, usage_date) bo‘lsa, qo‘shimcha (user_id, usage_date) indeksi kerak emas.
-- =============================================================================

-- Foydalanuvchi Telegram id (bot kodida users.id bilan bir xil, lekin alohida ustun bo‘lsa tezlashtiradi)
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON public.users (telegram_id);

-- Tarif limitlari: service_usage_buckets — user_id + bucket_key
CREATE INDEX IF NOT EXISTS idx_service_usage_buckets_user_bucket
  ON public.service_usage_buckets (user_id, bucket_key);

-- Obuna qatorlari: eng yangi yozuvlarni tartiblash (kod created_at ni tanlaydi)
ALTER TABLE public.premium_subscriptions
  ADD COLUMN IF NOT EXISTS created_at timestamptz DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_premium_subscriptions_user
  ON public.premium_subscriptions (user_id);

CREATE INDEX IF NOT EXISTS idx_premium_subscriptions_user_created
  ON public.premium_subscriptions (user_id, created_at DESC NULLS LAST);

-- Audit: usage_logs (db_insert_action_log fallback)
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_created
  ON public.usage_logs (user_id, created_at DESC NULLS LAST);

-- To‘lovlar ro‘yxati (user_id bo‘yicha)
ALTER TABLE public.payments ADD COLUMN IF NOT EXISTS created_at timestamptz DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_payments_user_created
  ON public.payments (user_id, created_at DESC NULLS LAST);
