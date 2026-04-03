-- =============================================================================
-- To‘lov turlari va hujjat ruxsatlari (mavjud Supabase loyiha uchun)
-- SQL Editor da yuqoridan pastga BITTA skript sifatida ishga tushiring.
--
-- MUHIM: `SET status = ...` qatorini alohida ishga TUSHIRMANG — bu faqat UPDATE ichida
--        yaroqli. Doim WITH ... UPDATE ... butun blokini yuboring.
--
-- MUHIM: unique indeksdan OLDIN takroriy pending qatorlar bo‘lmasligi kerak.
-- =============================================================================

-- Hujjat tarifi (admin tasdiqlagach bot/API tekshirishi mumkin)
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS has_cv_access boolean DEFAULT false NOT NULL;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS has_objective_access boolean DEFAULT false NOT NULL;

COMMENT ON COLUMN public.users.has_cv_access IS 'Bir martalik CV to‘lovi tasdiqlangan';
COMMENT ON COLUMN public.users.has_objective_access IS 'Bir martalik obyektivka to‘lovi tasdiqlangan';

-- =============================================================================
-- 1) Takroriy PENDING to‘lovlarni tozalash
--    Har bir user_id uchun faqat eng katta id li bitta pending qoladi.
--    Qolganlari rejected.
--
--    status ustuni payment_status_enum bo‘lsa — quyidagi TO‘LIQ blok ishlatiladi.
--    Agar status oddiy TEXT bo‘lsa: SET va WHERE ichidagi ::public.payment_status_enum
--    qismlarini olib tashlang (faqat 'rejected' va 'pending' qoldiring).
-- =============================================================================
WITH ranked AS (
  SELECT
    id,
    ROW_NUMBER() OVER (
      PARTITION BY user_id
      ORDER BY id DESC
    ) AS rn
  FROM public.payments
  WHERE status = 'pending'::public.payment_status_enum
)
UPDATE public.payments AS p
SET status = 'rejected'::public.payment_status_enum
FROM ranked AS r
WHERE p.id = r.id
  AND r.rn > 1;

-- =============================================================================
-- 2) Bir user — bir pending (indeks)
--    ENUM bo‘lsa va indeks xato bersa: WHERE status = 'pending'::public.payment_status_enum
-- =============================================================================
CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_one_pending_per_user
  ON public.payments (user_id)
  WHERE status = 'pending'::public.payment_status_enum;

-- Eslatma: payments.plan_type qiymatlari (kod bilan mos):
--   'cv', 'objective' — 5000 so‘m (SINGLE_DOC_PRICE_UZS)
--   'premium' — PREMIUM_PRICE_UZS (masalan 29999)
--   'standard' — STANDARD_PRICE_UZS
