-- Kategoriyali limitlar (Standard / Premium / Oddiy tariflar bo'yicha)
-- Supabase SQL Editor'da ishga tushiring (bir marta).

CREATE TABLE IF NOT EXISTS public.service_usage_buckets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id bigint NOT NULL,
  bucket_key text NOT NULL,
  count int NOT NULL DEFAULT 0,
  updated_at timestamptz DEFAULT now(),
  UNIQUE (user_id, bucket_key)
);

CREATE INDEX IF NOT EXISTS idx_service_usage_buckets_user
  ON public.service_usage_buckets (user_id);

ALTER TABLE public.service_usage_buckets DISABLE ROW LEVEL SECURITY;
