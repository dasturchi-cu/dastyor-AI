-- Faqat shu muammo bo‘lsa (PGRST204: metadata column topilmadi):
-- SQL Editor da bir marta ishga tushiring. Keyin Supabase API odatda 1–2 daqiqada yangilanadi.

ALTER TABLE public.payments ADD COLUMN IF NOT EXISTS metadata jsonb;
COMMENT ON COLUMN public.payments.metadata IS 'To‘lov qo‘shimcha JSON';
