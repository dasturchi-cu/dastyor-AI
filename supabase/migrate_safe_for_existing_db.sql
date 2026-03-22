-- =============================================================================
-- MAVJUD Supabase loyiha uchun (sizda allaqachon users, logs, payments va hokazo bor)
-- Butun schema.sql ni QAYTA ishlatmang — faqat shu faylni bitta marta ishga tushiring.
--
-- Agar bot/API bazaga yozmasa: avvalo server .env da SUPABASE_SERVICE_ROLE_KEY,
-- yoki rls_fix_backend_writes.sql (RLS o'chirish).
-- =============================================================================

-- Kod kutadigan users ustunlari (bor bo'lsa hech narsa qilmaydi)
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS user_plan text DEFAULT 'standard';
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS daily_limit integer DEFAULT 10;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS used_count integer DEFAULT 0;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS usage_count integer DEFAULT 0;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS limit_count integer;

-- logs: Python db_insert_action_log uchun
ALTER TABLE public.logs ADD COLUMN IF NOT EXISTS action_type text;
ALTER TABLE public.logs ADD COLUMN IF NOT EXISTS file_name text;
ALTER TABLE public.logs ADD COLUMN IF NOT EXISTS metadata jsonb;
ALTER TABLE public.logs ADD COLUMN IF NOT EXISTS created_at timestamptz DEFAULT now();

-- Indekslar (mavjud bo'lsa xato bermaydi)
CREATE INDEX IF NOT EXISTS idx_logs_user_id ON public.logs (user_id);
CREATE INDEX IF NOT EXISTS idx_logs_created_at ON public.logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_logs_action ON public.logs (action_type);
CREATE INDEX IF NOT EXISTS idx_users_user_plan ON public.users (user_plan);
