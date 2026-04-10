-- =============================================================================
-- PRODUCTION REQUIRED SCHEMA (RUN-READY) — Supabase SQL Editor
--
-- This file creates the tables you requested (UUID primary keys) in `public`.
-- It is SAFE to run multiple times (IF NOT EXISTS everywhere).
--
-- IMPORTANT:
-- - Your current codebase already uses existing tables like `public.users` with
--   `bigint` ids (Telegram ID). Migrating a live system to UUID-based `users`
--   requires a coordinated code migration.
-- - If your project ALREADY has a `public.users` table, this script will NOT
--   overwrite it. Instead, it creates `public.users_v2` + related *_v2 tables,
--   so you can migrate safely without breaking running features.
-- - Once the backend is migrated, you can rename `*_v2` tables to the canonical
--   names in a controlled maintenance window.
-- =============================================================================

-- Extensions commonly needed for UUID generation
create extension if not exists "pgcrypto";

-- -----------------------------------------------------------------------------
-- USERS (v2) — required shape
-- -----------------------------------------------------------------------------
create table if not exists public.users_v2 (
  id uuid primary key default gen_random_uuid(),
  telegram_id bigint not null unique,
  name text,
  created_at timestamptz not null default now(),
  referred_by uuid null
);

-- Self-referential FK (nullable)
do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'users_v2_referred_by_fkey'
  ) then
    alter table public.users_v2
      add constraint users_v2_referred_by_fkey
      foreign key (referred_by)
      references public.users_v2(id)
      on delete set null;
  end if;
end$$;

create index if not exists idx_users_v2_telegram_id on public.users_v2 (telegram_id);
create index if not exists idx_users_v2_created_at on public.users_v2 (created_at desc);
create index if not exists idx_users_v2_referred_by on public.users_v2 (referred_by);

-- -----------------------------------------------------------------------------
-- REFERRALS (v2)
-- Requirements:
-- - Count ONLY new users
-- - Prevent duplicate counting
-- - Enforce UNIQUE(new_user_id)
-- -----------------------------------------------------------------------------
create table if not exists public.referrals_v2 (
  id uuid primary key default gen_random_uuid(),
  referrer_id uuid not null references public.users_v2(id) on delete cascade,
  new_user_id uuid not null unique references public.users_v2(id) on delete cascade,
  created_at timestamptz not null default now()
);

create index if not exists idx_referrals_v2_referrer_id on public.referrals_v2 (referrer_id);
create index if not exists idx_referrals_v2_created_at on public.referrals_v2 (created_at desc);

-- -----------------------------------------------------------------------------
-- FILES (v2) — metadata for Supabase Storage objects
-- -----------------------------------------------------------------------------
create table if not exists public.files_v2 (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users_v2(id) on delete cascade,
  file_url text not null,
  file_type text not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_files_v2_user_id on public.files_v2 (user_id);
create index if not exists idx_files_v2_created_at on public.files_v2 (created_at desc);

-- -----------------------------------------------------------------------------
-- LOGS (v2) — production audit trail
-- -----------------------------------------------------------------------------
create table if not exists public.logs_v2_required (
  id uuid primary key default gen_random_uuid(),
  user_id uuid null references public.users_v2(id) on delete set null,
  action text not null,
  metadata jsonb null,
  created_at timestamptz not null default now()
);

create index if not exists idx_logs_v2_required_user_id on public.logs_v2_required (user_id);
create index if not exists idx_logs_v2_required_created_at on public.logs_v2_required (created_at desc);
create index if not exists idx_logs_v2_required_action on public.logs_v2_required (action);

-- -----------------------------------------------------------------------------
-- Helper: atomically register referral (v2)
-- - Inserts referral only once per new_user_id
-- - Links users_v2.referred_by if empty
-- -----------------------------------------------------------------------------
create or replace function public.register_referral_v2(p_referrer_telegram_id bigint, p_new_user_telegram_id bigint)
returns json
language plpgsql
security definer
set search_path = public
as $$
declare
  referrer_uuid uuid;
  new_user_uuid uuid;
  inserted boolean := false;
begin
  if p_referrer_telegram_id is null or p_new_user_telegram_id is null then
    return json_build_object('ok', false, 'reason', 'missing');
  end if;
  if p_referrer_telegram_id = p_new_user_telegram_id then
    return json_build_object('ok', false, 'reason', 'self');
  end if;

  select id into referrer_uuid from public.users_v2 where telegram_id = p_referrer_telegram_id;
  select id into new_user_uuid from public.users_v2 where telegram_id = p_new_user_telegram_id;

  if referrer_uuid is null or new_user_uuid is null then
    return json_build_object('ok', false, 'reason', 'user_not_found');
  end if;

  -- best-effort: attach referred_by if not set
  update public.users_v2
    set referred_by = referrer_uuid
    where id = new_user_uuid and referred_by is null;

  begin
    insert into public.referrals_v2 (referrer_id, new_user_id)
    values (referrer_uuid, new_user_uuid);
    inserted := true;
  exception when unique_violation then
    inserted := false;
  end;

  return json_build_object('ok', true, 'inserted', inserted);
end;
$$;

grant execute on function public.register_referral_v2(bigint, bigint) to anon, authenticated, service_role;

