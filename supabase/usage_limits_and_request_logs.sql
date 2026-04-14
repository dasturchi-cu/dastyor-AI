-- =============================================================================
-- DASTYOR AI — Usage limits (daily, per-feature) + request logs (jobs/audit)
--
-- Goal:
-- - Single source of truth for web + bot usage counters
-- - Atomic quota consumption (race-safe)
-- - Full request audit trail for debugging hangs/500s
--
-- Safe to run multiple times (IF NOT EXISTS).
-- =============================================================================

create extension if not exists "pgcrypto";

-- -----------------------------------------------------------------------------
-- subscriptions (canonical table; existing deployments may also have premium_subscriptions)
-- -----------------------------------------------------------------------------
create table if not exists public.subscriptions (
  id bigserial primary key,
  user_id bigint not null references public.users(id) on delete cascade,
  plan text not null check (plan in ('free','standard','premium')),
  status text not null default 'active' check (status in ('active','expired','cancelled')),
  start_date timestamptz not null default now(),
  end_date timestamptz,
  provider text,
  provider_ref text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_subscriptions_user_status_end
  on public.subscriptions(user_id, status, end_date desc);

-- -----------------------------------------------------------------------------
-- usage_limits (strict daily caps per feature)
-- -----------------------------------------------------------------------------
create table if not exists public.usage_limits (
  user_id bigint not null references public.users(id) on delete cascade,
  feature text not null check (feature in ('spell','translate','translit')),
  day date not null,
  used int not null default 0,
  updated_at timestamptz not null default now(),
  primary key (user_id, feature, day)
);

create index if not exists idx_usage_limits_day on public.usage_limits(day);
create index if not exists idx_usage_limits_user_day on public.usage_limits(user_id, day);

-- -----------------------------------------------------------------------------
-- request_logs (every processing request, including queued background jobs)
-- -----------------------------------------------------------------------------
create table if not exists public.request_logs (
  id uuid primary key default gen_random_uuid(),
  user_id bigint references public.users(id) on delete set null,
  channel text not null check (channel in ('web','bot')),
  feature text not null check (feature in ('spell','translate','translit')),
  input_type text not null check (input_type in ('text','file')),
  status text not null check (status in ('queued','running','succeeded','failed','blocked')),
  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  duration_ms int,
  request_id text,
  error_code text,
  error_message text,
  meta jsonb not null default '{}'::jsonb,
  storage_in jsonb,
  storage_out jsonb
);

create index if not exists idx_request_logs_user_created on public.request_logs(user_id, created_at desc);
create index if not exists idx_request_logs_status_created on public.request_logs(status, created_at desc);
create index if not exists idx_request_logs_feature_created on public.request_logs(feature, created_at desc);

-- -----------------------------------------------------------------------------
-- RPC: consume daily quota atomically (race-safe)
-- Returns:
--   allowed: boolean
--   used: used count after (or current if blocked)
--   remaining: remaining after (or current if blocked)
-- -----------------------------------------------------------------------------
create or replace function public.consume_daily_quota(
  p_user_id bigint,
  p_feature text,
  p_day date,
  p_cap int
) returns table(allowed boolean, used int, remaining int)
language plpgsql
security definer
set search_path = public
as $$
declare
  v_used int;
  v_cap int;
begin
  v_cap := greatest(0, coalesce(p_cap, 0));
  if v_cap < 1 then
    return query select false, 0, 0;
    return;
  end if;

  insert into public.usage_limits(user_id, feature, day, used)
  values (p_user_id, p_feature, p_day, 0)
  on conflict (user_id, feature, day) do nothing;

  update public.usage_limits
  set used = used + 1, updated_at = now()
  where user_id = p_user_id and feature = p_feature and day = p_day and used < v_cap
  returning used into v_used;

  if v_used is null then
    select ul.used into v_used
    from public.usage_limits ul
    where ul.user_id = p_user_id and ul.feature = p_feature and ul.day = p_day;
    v_used := coalesce(v_used, 0);
    return query select false, v_used, greatest(0, v_cap - v_used);
    return;
  end if;

  return query select true, v_used, greatest(0, v_cap - v_used);
end;
$$;

grant execute on function public.consume_daily_quota(bigint, text, date, int) to anon, authenticated, service_role;

