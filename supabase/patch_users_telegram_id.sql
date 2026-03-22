-- =============================================================================
-- Faqat shu skriptni Supabase SQL Editor da ishga tushiring.
-- schema.sql ichidagi "telegram_id bigint ..." qatorini KO'CHIRIB ISHLATMANG — 42601 xato beradi.
-- =============================================================================

ALTER TABLE public.users ADD COLUMN IF NOT EXISTS telegram_id bigint;

UPDATE public.users
SET telegram_id = id
WHERE telegram_id IS NULL;

-- Ixtiyoriy: barcha qatorlar to'ldirilgach NOT NULL qilish (xato bo'lsa shu qatorni o'tkazib yuboring)
-- ALTER TABLE public.users ALTER COLUMN telegram_id SET NOT NULL;
