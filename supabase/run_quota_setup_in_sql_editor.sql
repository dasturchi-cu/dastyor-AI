-- =============================================================================
-- Supabase → SQL Editor → yangi query → BUTUN USHBU FAYLNI nusxalab RUN qiling.
-- (Fayl nomini emas — faqat quyidagi SQL matn.)
-- =============================================================================

-- 1) Jadval (limit hisoblagichlar)
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

-- 2) Atomik +1 (bot/API bir xil bazadan o‘qisin)
CREATE OR REPLACE FUNCTION public.increment_service_bucket(p_user_id bigint, p_bucket_key text)
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  new_count integer;
BEGIN
  INSERT INTO public.service_usage_buckets (user_id, bucket_key, count, updated_at)
  VALUES (p_user_id, p_bucket_key, 1, now())
  ON CONFLICT (user_id, bucket_key)
  DO UPDATE SET
    count = public.service_usage_buckets.count + 1,
    updated_at = now()
  RETURNING count INTO new_count;
  RETURN new_count;
END;
$$;

GRANT EXECUTE ON FUNCTION public.increment_service_bucket(bigint, text) TO anon, authenticated, service_role;

-- 2b) Limitdan oshmaydigan atomik +1 (parallel so‘rovlar: ishlatilgan > limit bo‘lmasin)
CREATE OR REPLACE FUNCTION public.try_increment_service_bucket(
  p_user_id bigint,
  p_bucket_key text,
  p_cap integer
)
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  cur int;
  new_c int;
BEGIN
  IF p_cap IS NULL OR p_cap < 1 THEN
    RETURN 0;
  END IF;

  PERFORM pg_advisory_xact_lock(
    (hashtext(p_user_id::text || chr(0) || p_bucket_key))::bigint
  );

  SELECT count INTO cur
  FROM public.service_usage_buckets
  WHERE user_id = p_user_id AND bucket_key = p_bucket_key;

  IF NOT FOUND THEN
    INSERT INTO public.service_usage_buckets (user_id, bucket_key, count, updated_at)
    VALUES (p_user_id, p_bucket_key, 1, now());
    RETURN 1;
  END IF;

  IF cur >= p_cap THEN
    RETURN 0;
  END IF;

  UPDATE public.service_usage_buckets
  SET count = count + 1, updated_at = now()
  WHERE user_id = p_user_id AND bucket_key = p_bucket_key
  RETURNING count INTO new_c;

  RETURN COALESCE(new_c, 0);
END;
$$;

GRANT EXECUTE ON FUNCTION public.try_increment_service_bucket(bigint, text, integer) TO anon, authenticated, service_role;

-- 3) Ixtiyoriy: users jadvalida usage_count bo‘lsa ishlaydi; xato bersa 4-blocni o‘chirib qayta RUN qiling
CREATE OR REPLACE FUNCTION public.increment_user_action_counters(p_user_id bigint)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  UPDATE public.users SET
    usage_count = COALESCE(usage_count, 0) + 1,
    used_count = COALESCE(used_count, 0) + 1,
    activity_count = COALESCE(activity_count, 0) + 1
  WHERE id = p_user_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.increment_user_action_counters(bigint) TO anon, authenticated, service_role;
