-- Channel subscription gate + 1-time CV bonus flags
-- Safe to run multiple times.

ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS is_subscribed boolean DEFAULT false;

ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS bonus_used boolean DEFAULT false;

