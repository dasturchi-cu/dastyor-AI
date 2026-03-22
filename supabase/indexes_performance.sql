-- Supabase SQL Editor: tez-tez ishlatiladigan filtrlarga indeks (plan/limit so'rovlari).
-- Bir marta ishga tushiring.

CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON public.users (telegram_id);

CREATE INDEX IF NOT EXISTS idx_service_usage_buckets_user_bucket
  ON public.service_usage_buckets (user_id, bucket_key);

CREATE INDEX IF NOT EXISTS idx_daily_usage_user_date
  ON public.daily_usage (user_id, usage_date);

CREATE INDEX IF NOT EXISTS idx_premium_subscriptions_user
  ON public.premium_subscriptions (user_id);
