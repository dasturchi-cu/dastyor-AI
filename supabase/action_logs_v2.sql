-- =============================================================================
-- DASTYOR AI — Complete action logging (v2)
--
-- Purpose: track every user action without slowing the bot/API.
-- This creates a NEW table to avoid breaking existing public.logs schema.
--
-- Run in Supabase SQL Editor.
-- =============================================================================

-- Required for gen_random_uuid()
create extension if not exists pgcrypto;

create table if not exists public.logs_v2 (
  id uuid primary key default gen_random_uuid(),
  telegram_id bigint not null,
  username text,
  action_type text not null,
  details text,
  metadata jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_logs_v2_telegram_id on public.logs_v2 (telegram_id);
create index if not exists idx_logs_v2_created_at on public.logs_v2 (created_at desc);
create index if not exists idx_logs_v2_action_type on public.logs_v2 (action_type);

-- Optional: common rollup filters
create index if not exists idx_logs_v2_action_created on public.logs_v2 (action_type, created_at desc);

-- If you use RLS, keep it consistent with the rest of the project.
alter table public.logs_v2 enable row level security;

-- Service role bypasses RLS automatically. If you need anon inserts for a public webapp,
-- create policies carefully. Recommended: keep inserts server-side only.

-- =============================================================================
-- Analytics queries (examples)
-- =============================================================================
-- 1) Total usage per user (all time)
-- select telegram_id, coalesce(max(username), '') as username, count(*) as total
-- from public.logs_v2
-- group by telegram_id
-- order by total desc;
--
-- 2) Most used features (all time)
-- select action_type, count(*) as total
-- from public.logs_v2
-- group by action_type
-- order by total desc;
--
-- 3) Daily usage stats (by action_type)
-- select date_trunc('day', created_at) as day, action_type, count(*) as total
-- from public.logs_v2
-- group by 1,2
-- order by day desc, total desc;
--
-- 4) Top users today
-- select telegram_id, coalesce(max(username), '') as username, count(*) as total
-- from public.logs_v2
-- where created_at >= date_trunc('day', now())
-- group by telegram_id
-- order by total desc
-- limit 50;

