-- =============================================================================
-- DASTYOR AI — Real-time observability table: system_logs
-- Tracks START/END/ERROR/CLICK with duration and metadata.
-- Run in Supabase SQL Editor.
-- =============================================================================

create extension if not exists pgcrypto;

create table if not exists public.system_logs (
  id uuid primary key default gen_random_uuid(),
  telegram_id bigint,
  username text,
  event_type text not null,          -- START | END | ERROR | CLICK | HTTP
  action_name text not null,         -- cv_create, ocr, translate, api:/api/translate, etc
  status text,                       -- success | failed | blocked | ok
  error_message text,
  execution_time_ms int,
  metadata jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_system_logs_created_at on public.system_logs (created_at desc);
create index if not exists idx_system_logs_action on public.system_logs (action_name);
create index if not exists idx_system_logs_event on public.system_logs (event_type);
create index if not exists idx_system_logs_user on public.system_logs (telegram_id);
create index if not exists idx_system_logs_action_created on public.system_logs (action_name, created_at desc);

alter table public.system_logs enable row level security;

-- Recommended: keep inserts server-side using service_role key.

-- =============================================================================
-- Useful queries
-- =============================================================================
-- Slow actions (>2000ms) in last 24h
-- select created_at, telegram_id, username, action_name, execution_time_ms, status
-- from public.system_logs
-- where created_at > now() - interval '24 hours'
--   and execution_time_ms >= 2000
-- order by execution_time_ms desc
-- limit 200;
--
-- Errors in last 24h
-- select created_at, telegram_id, username, action_name, error_message, metadata
-- from public.system_logs
-- where created_at > now() - interval '24 hours'
--   and event_type = 'ERROR'
-- order by created_at desc
-- limit 200;
--
-- Real-time "what is happening now" (last 2 minutes)
-- select created_at, event_type, action_name, status, telegram_id, username
-- from public.system_logs
-- where created_at > now() - interval '2 minutes'
-- order by created_at desc
-- limit 300;

