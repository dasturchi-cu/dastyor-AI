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

-- Trigger: API telegram_id yubormasa ham INSERT paytida avtomatik id dan to'ldiriladi (23502 oldini olish)
CREATE OR REPLACE FUNCTION public.users_fill_telegram_id()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.telegram_id IS NULL THEN
    NEW.telegram_id := NEW.id;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_users_fill_telegram_id ON public.users;
CREATE TRIGGER trg_users_fill_telegram_id
  BEFORE INSERT OR UPDATE ON public.users
  FOR EACH ROW
  EXECUTE FUNCTION public.users_fill_telegram_id();
