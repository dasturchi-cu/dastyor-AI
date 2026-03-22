-- Atomik quota: race condition va read-modify-write o'rniga DB ichida increment.
-- Supabase SQL Editor da bir marta ishga tushiring.
-- service_usage_buckets: UNIQUE (user_id, bucket_key) bo'lishi kerak (service_usage_buckets.sql).

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

GRANT EXECUTE ON FUNCTION public.increment_service_bucket(bigint, text) TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.increment_user_action_counters(bigint) TO anon, authenticated, service_role;
