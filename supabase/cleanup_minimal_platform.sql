-- ============================================================================
-- SUPABASE FULL CLEANUP + HARDENING SCRIPT
-- Target: CV + Objective/Obyektivka + Admin Murojaat + Payments + Bot Alerts
-- Safe/idempotent, production-oriented. Run in STAGING first.
-- ============================================================================

begin;

set local statement_timeout = '0';
set local lock_timeout = '10s';
set local idle_in_transaction_session_timeout = '10min';

-- Prevent concurrent maintenance runs.
select pg_advisory_xact_lock(hashtext('supabase_full_cleanup_minimal_platform_v2'));

-- Compatibility shim: some legacy DB objects compare text to enum directly
-- (e.g. text = payment_status_enum) and fail before cleanup can run.
-- We temporarily define missing operators so the migration can proceed.
do $$
begin
  if exists (
    select 1
    from pg_type t
    join pg_namespace n on n.oid = t.typnamespace
    where n.nspname = 'public'
      and t.typname = 'payment_status_enum'
  ) then
    execute $q$
      create or replace function public._eq_text_payment_status_enum(left_text text, right_enum public.payment_status_enum)
      returns boolean
      language sql
      immutable
      as 'select left_text = right_enum::text';
    $q$;

    if not exists (
      select 1
      from pg_operator o
      join pg_namespace n on n.oid = o.oprnamespace
      where n.nspname = 'public'
        and o.oprname = '='
        and o.oprleft = 'text'::regtype
        and o.oprright = 'public.payment_status_enum'::regtype
    ) then
      execute 'create operator public.= (leftarg = text, rightarg = public.payment_status_enum, procedure = public._eq_text_payment_status_enum)'; 
    end if;
  end if;
exception when others then
  raise notice 'Compatibility shim skipped: %', sqlerrm;
end$$;

-- Preflight 0: drop old views/policies/constraints that may lock enum-dependent expressions.
do $$
declare
  r record;
begin
  -- Drop all public views/materialized views (legacy dashboards/analytics/etc).
  for r in
    select table_name
    from information_schema.views
    where table_schema = 'public'
  loop
    execute format('drop view if exists public.%I cascade', r.table_name);
  end loop;

  for r in
    select matviewname
    from pg_matviews
    where schemaname = 'public'
  loop
    execute format('drop materialized view if exists public.%I cascade', r.matviewname);
  end loop;

  -- Drop old policies early so enum/text expressions inside policies do not block casts.
  for r in
    select schemaname, tablename, policyname
    from pg_policies
    where schemaname = 'public'
      and tablename in ('users', 'payments', 'paid_doc_requests', 'support_requests')
  loop
    execute format('drop policy if exists %I on %I.%I', r.policyname, r.schemaname, r.tablename);
  end loop;

  -- Drop old CHECK constraints on enum-prone columns before type conversion.
  for r in
    select con.conname as constraint_name, cls.relname as table_name
    from pg_constraint con
    join pg_class cls on cls.oid = con.conrelid
    join pg_namespace nsp on nsp.oid = cls.relnamespace
    where nsp.nspname = 'public'
      and con.contype = 'c'
      and cls.relname in ('users', 'payments', 'paid_doc_requests', 'support_requests')
      and pg_get_constraintdef(con.oid) ilike any(array[
        '%status%',
        '%plan_type%',
        '%kind%',
        '%source%',
        '%premium%',
        '%subscription%',
        '%referral%'
      ])
  loop
    execute format('alter table public.%I drop constraint if exists %I', r.table_name, r.constraint_name);
  end loop;
end$$;

-- Preflight: normalize legacy enum-like columns to text to avoid operator/type errors.
do $$
declare
  r record;
begin
  for r in
    select c.table_name, c.column_name
    from information_schema.columns c
    where c.table_schema = 'public'
      and c.table_name in ('users', 'payments', 'paid_doc_requests', 'support_requests')
      and c.column_name in ('status', 'kind', 'plan_type', 'source')
      and c.data_type = 'USER-DEFINED'
  loop
    begin
      execute format('alter table public.%I alter column %I drop default', r.table_name, r.column_name);
    exception when others then
      null;
    end;

    begin
      execute format(
        'alter table public.%I alter column %I type text using %I::text',
        r.table_name, r.column_name, r.column_name
      );
      raise notice 'Preflight casted %.% to text', r.table_name, r.column_name;
    exception when others then
      raise notice 'Preflight cast skipped %.% (%).', r.table_name, r.column_name, sqlerrm;
    end;
  end loop;
end$$;

-- ============================================================================
-- 1) TABLE CLEANUP
-- ============================================================================

-- Drop explicit known legacy tables first.
drop table if exists public.ocr_jobs cascade;
drop table if exists public.translation_jobs cascade;
drop table if exists public.translit_jobs cascade;
drop table if exists public.spellcheck_jobs cascade;
drop table if exists public.pdf_jobs cascade;
drop table if exists public.referrals cascade;
drop table if exists public.premium_subscriptions cascade;
drop table if exists public.subscriptions cascade;
drop table if exists public.subscription_history cascade;
drop table if exists public.balance_logs cascade;
drop table if exists public.usage_logs cascade;
drop table if exists public.daily_usage cascade;
drop table if exists public.service_usage_buckets cascade;
drop table if exists public.logs_v2 cascade;
drop table if exists public.analytics_events cascade;
drop table if exists public.experiments cascade;

-- Dynamic cleanup: drop any PUBLIC table not in allowlist.
do $$
declare
  r record;
  v_keep_tables text[] := array[
    'users',
    'payments',
    'paid_doc_requests',
    'support_requests',
    'action_logs',
    'system_logs'
  ];
begin
  for r in
    select t.table_name
    from information_schema.tables t
    where t.table_schema = 'public'
      and t.table_type = 'BASE TABLE'
      and t.table_name <> all(v_keep_tables)
  loop
    execute format('drop table if exists public.%I cascade', r.table_name);
    raise notice 'Dropped legacy table: public.%', r.table_name;
  end loop;
end$$;

-- ============================================================================
-- 2) COLUMN CLEANUP
-- ============================================================================

-- Ensure core tables exist before column/index/policy operations.
create table if not exists public.users (
  id bigint primary key,
  first_name text,
  username text,
  telegram_id bigint,
  files_processed integer not null default 0,
  sessions integer not null default 0,
  joined_at timestamptz not null default now(),
  last_active timestamptz not null default now(),
  pending_oby_json jsonb,
  paywall_shown_at timestamptz
);

create table if not exists public.payments (
  id bigserial primary key,
  user_id bigint,
  plan_type text,
  amount_uzs numeric(14,2),
  status text,
  provider text,
  provider_txn_id text,
  screenshot_url text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.paid_doc_requests (
  id bigserial primary key,
  user_id bigint,
  kind text,
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'pending',
  payment_id bigint,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.action_logs (
  id bigserial primary key,
  user_id bigint,
  action text,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.system_logs (
  id bigserial primary key,
  level text,
  message text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- USERS table cleanup.
alter table if exists public.users
  add column if not exists id bigint,
  add column if not exists first_name text,
  add column if not exists username text,
  add column if not exists telegram_id bigint,
  add column if not exists files_processed integer not null default 0,
  add column if not exists sessions integer not null default 0,
  add column if not exists joined_at timestamptz not null default now(),
  add column if not exists last_active timestamptz not null default now(),
  add column if not exists pending_oby_json jsonb,
  add column if not exists paywall_shown_at timestamptz;

-- Drop legacy/premium/experimental columns from users when present.
alter table if exists public.users
  drop column if exists premium_until,
  drop column if exists premium_expires_at,
  drop column if exists subscription_plan,
  drop column if exists referral_code,
  drop column if exists referred_by,
  drop column if exists bonus_balance,
  drop column if exists total_spent,
  drop column if exists is_test,
  drop column if exists test_tag,
  drop column if exists experiment_group;

-- PAYMENTS table normalization.
alter table if exists public.payments
  add column if not exists id bigserial,
  add column if not exists user_id bigint,
  add column if not exists plan_type text,
  add column if not exists amount_uzs numeric(14,2),
  add column if not exists status text,
  add column if not exists provider text,
  add column if not exists provider_txn_id text,
  add column if not exists screenshot_url text,
  add column if not exists metadata jsonb not null default '{}'::jsonb,
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists updated_at timestamptz not null default now();

alter table if exists public.payments
  alter column plan_type type text using plan_type::text,
  alter column status type text using coalesce(status::text, 'pending');

alter table if exists public.payments
  drop column if exists premium_months,
  drop column if exists subscription_id,
  drop column if exists discount_percent,
  drop column if exists referral_discount,
  drop column if exists old_plan,
  drop column if exists campaign,
  drop column if exists test_mode;

-- PAID DOC REQUESTS normalization.
alter table if exists public.paid_doc_requests
  add column if not exists id bigserial,
  add column if not exists user_id bigint,
  add column if not exists kind text,
  add column if not exists payload jsonb not null default '{}'::jsonb,
  add column if not exists status text not null default 'pending',
  add column if not exists payment_id bigint,
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists updated_at timestamptz not null default now();

alter table if exists public.paid_doc_requests
  alter column kind type text using kind::text,
  alter column status type text using status::text;

alter table if exists public.paid_doc_requests
  drop column if exists premium_plan,
  drop column if exists referral_used,
  drop column if exists test_case,
  drop column if exists legacy_kind;

-- SUPPORT REQUESTS structure.
create table if not exists public.support_requests (
  id bigserial primary key,
  user_id bigint not null,
  username text,
  message text not null,
  source text not null default 'webapp',
  status text not null default 'open',
  created_at timestamptz not null default now(),
  resolved_at timestamptz,
  metadata jsonb not null default '{}'::jsonb
);

alter table if exists public.support_requests
  drop column if exists assigned_to,
  drop column if exists priority,
  drop column if exists tags,
  drop column if exists legacy_state;

alter table if exists public.support_requests
  add column if not exists user_id bigint,
  alter column status type text using status::text;

-- ============================================================================
-- 3) POLICY CLEANUP
-- ============================================================================

-- Remove ALL old public policies (safe) and re-create minimal policies.
do $$
declare
  r record;
begin
  for r in
    select schemaname, tablename, policyname
    from pg_policies
    where schemaname = 'public'
      and tablename in ('users', 'payments', 'paid_doc_requests', 'support_requests', 'action_logs', 'system_logs')
  loop
    execute format('drop policy if exists %I on %I.%I', r.policyname, r.schemaname, r.tablename);
  end loop;
end$$;

alter table if exists public.users enable row level security;
alter table if exists public.payments enable row level security;
alter table if exists public.paid_doc_requests enable row level security;
alter table if exists public.support_requests enable row level security;
alter table if exists public.action_logs enable row level security;
alter table if exists public.system_logs enable row level security;

-- Users: user can read/update own row. Service role bypasses RLS automatically.
create policy users_select_own on public.users
for select using (auth.uid()::text = id::text);

create policy users_update_own on public.users
for update using (auth.uid()::text = id::text)
with check (auth.uid()::text = id::text);

-- Payments: user can read own records only.
create policy payments_select_own on public.payments
for select using (auth.uid()::text = user_id::text);

-- Paid doc requests: user can read own records only.
create policy paid_doc_requests_select_own on public.paid_doc_requests
for select using (auth.uid()::text = user_id::text);

-- Support requests: user can create and read own records.
create policy support_requests_insert_own on public.support_requests
for insert with check (auth.uid()::text = user_id::text);

create policy support_requests_select_own on public.support_requests
for select using (auth.uid()::text = user_id::text);

-- Logs: no anon/auth direct access.
-- (No read/write policy intentionally; service role only.)

-- ============================================================================
-- 4) FUNCTION CLEANUP
-- ============================================================================

-- Drop explicit legacy RPC/functions.
drop function if exists public.register_referral(bigint, bigint) cascade;
drop function if exists public.consume_referral_discount(bigint, text) cascade;
drop function if exists public.increment_service_bucket(bigint, text) cascade;
drop function if exists public.try_increment_service_bucket(bigint, text, integer) cascade;
drop function if exists public.increment_user_action_counters(bigint) cascade;

-- Dynamic cleanup by suspicious/legacy function naming.
do $$
declare
  r record;
begin
  for r in
    select n.nspname as schema_name,
           p.proname as fn_name,
           pg_get_function_identity_arguments(p.oid) as fn_args
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
      and (
        p.proname ilike '%premium%'
        or p.proname ilike '%referral%'
        or p.proname ilike '%ocr%'
        or p.proname ilike '%translate%'
        or p.proname ilike '%translit%'
        or p.proname ilike '%spell%'
        or p.proname ilike '%bucket%'
        or p.proname ilike '%subscription%'
        or p.proname ilike '%experiment%'
      )
  loop
    execute format('drop function if exists %I.%I(%s) cascade', r.schema_name, r.fn_name, r.fn_args);
    raise notice 'Dropped legacy function: %.%(%)', r.schema_name, r.fn_name, r.fn_args;
  end loop;
end$$;

-- ============================================================================
-- 5) STORAGE CLEANUP
-- ============================================================================

-- Keep only bucket used by current platform.
do $$
declare
  r record;
begin
  for r in
    select id from storage.buckets where id not in ('files')
  loop
    -- Direct deletion from storage.objects is blocked by Supabase protection trigger.
    -- Keep DB migration safe: do not delete here; clean via Storage API/CLI after migration.
    raise notice 'Storage cleanup pending via API for bucket: %', r.id;
  end loop;
end$$;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'files',
  'files',
  false,
  15728640,
  array[
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'image/jpeg',
    'image/png',
    'text/plain'
  ]
)
on conflict (id) do update
set public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

-- Remove old storage policies and define minimal secured policy.
do $$
declare
  r record;
begin
  for r in
    select schemaname, tablename, policyname
    from pg_policies
    where schemaname = 'storage'
      and tablename = 'objects'
  loop
    execute format('drop policy if exists %I on %I.%I', r.policyname, r.schemaname, r.tablename);
  end loop;
end$$;

-- Storage objects hardening (permission-safe). Some projects do not allow altering storage.objects.
do $$
begin
  begin
    execute 'alter table storage.objects enable row level security';
  exception when insufficient_privilege then
    raise notice 'Skipping storage.objects RLS (insufficient privilege).';
  end;

  begin
    execute $sql$
      create policy storage_objects_select_own on storage.objects
      for select using (
        bucket_id = 'files'
        and auth.role() = 'authenticated'
        and split_part(name, '/', 1) = auth.uid()::text
      )
    $sql$;
  exception when duplicate_object then
    null;
  when insufficient_privilege then
    raise notice 'Skipping policy storage_objects_select_own (insufficient privilege).';
  end;

  begin
    execute $sql$
      create policy storage_objects_insert_own on storage.objects
      for insert with check (
        bucket_id = 'files'
        and auth.role() = 'authenticated'
        and split_part(name, '/', 1) = auth.uid()::text
      )
    $sql$;
  exception when duplicate_object then
    null;
  when insufficient_privilege then
    raise notice 'Skipping policy storage_objects_insert_own (insufficient privilege).';
  end;

  begin
    execute $sql$
      create policy storage_objects_update_own on storage.objects
      for update using (
        bucket_id = 'files'
        and auth.role() = 'authenticated'
        and split_part(name, '/', 1) = auth.uid()::text
      )
      with check (
        bucket_id = 'files'
        and auth.role() = 'authenticated'
        and split_part(name, '/', 1) = auth.uid()::text
      )
    $sql$;
  exception when duplicate_object then
    null;
  when insufficient_privilege then
    raise notice 'Skipping policy storage_objects_update_own (insufficient privilege).';
  end;

  begin
    execute $sql$
      create policy storage_objects_delete_own on storage.objects
      for delete using (
        bucket_id = 'files'
        and auth.role() = 'authenticated'
        and split_part(name, '/', 1) = auth.uid()::text
      )
    $sql$;
  exception when duplicate_object then
    null;
  when insufficient_privilege then
    raise notice 'Skipping policy storage_objects_delete_own (insufficient privilege).';
  end;
end$$;

-- ============================================================================
-- 6) INDEX CLEANUP
-- ============================================================================

-- Remove duplicate/suspicious legacy indexes in public schema.
do $$
declare
  r record;
begin
  for r in
    select i.indexname
    from pg_indexes i
    where i.schemaname = 'public'
      and (
        i.indexname ilike '%premium%'
        or i.indexname ilike '%referral%'
        or i.indexname ilike '%ocr%'
        or i.indexname ilike '%translate%'
        or i.indexname ilike '%translit%'
        or i.indexname ilike '%spell%'
        or i.indexname ilike '%subscription%'
        or i.indexname ilike '%bucket%'
        or i.indexname ilike '%experiment%'
      )
  loop
    execute format('drop index if exists public.%I', r.indexname);
    raise notice 'Dropped legacy index: public.%', r.indexname;
  end loop;
end$$;

-- Recreate clean indexes for core workload.
create unique index if not exists idx_users_id_uniq on public.users (id);
create index if not exists idx_users_username on public.users (username);
create index if not exists idx_users_last_active_desc on public.users (last_active desc);

create index if not exists idx_payments_user_created_desc on public.payments (user_id, created_at desc);
create index if not exists idx_payments_status_created_desc on public.payments (status, created_at desc);
create unique index if not exists idx_payments_provider_txn_id_uniq on public.payments (provider_txn_id)
  where provider_txn_id is not null;

create index if not exists idx_paid_doc_requests_user_created_desc on public.paid_doc_requests (user_id, created_at desc);
create index if not exists idx_paid_doc_requests_status_created_desc on public.paid_doc_requests (status, created_at desc);
create index if not exists idx_paid_doc_requests_kind_created_desc on public.paid_doc_requests (kind, created_at desc);

create index if not exists idx_support_requests_user_created_desc on public.support_requests (user_id, created_at desc);
create index if not exists idx_support_requests_status_created_desc on public.support_requests (status, created_at desc);

do $$
begin
  if exists (
    select 1
    from information_schema.columns
    where table_schema='public' and table_name='action_logs' and column_name='user_id'
  ) then
    execute 'create index if not exists idx_action_logs_user_created_desc on public.action_logs (user_id, created_at desc)';
  end if;
end$$;
create index if not exists idx_system_logs_created_desc on public.system_logs (created_at desc);

-- ============================================================================
-- 7) DATA CLEANUP
-- ============================================================================

-- Remove premium/legacy kinds and statuses.
delete from public.payments
where coalesce(lower(plan_type::text), '') not in ('cv', 'objective', 'obyektivka');

delete from public.paid_doc_requests
where coalesce(lower(kind::text), '') not in ('cv', 'objective', 'obyektivka');

-- Keep only known statuses for core flows.
update public.payments
set status = 'pending'
where coalesce(status::text, '') not in ('pending', 'approved', 'rejected', 'paid', 'failed', 'cancelled');

update public.paid_doc_requests
set status = 'pending'
where coalesce(status::text, '') not in ('pending', 'approved', 'rejected', 'completed', 'cancelled');

update public.support_requests
set status = 'open'
where coalesce(status::text, '') not in ('open', 'resolved', 'closed');

-- Remove obvious test / fake rows.
delete from public.users
where coalesce(username, '') ilike any(array['test%', '%demo%', '%sample%', '%dummy%'])
   or coalesce(first_name, '') ilike any(array['test%', '%demo%', '%sample%', '%dummy%']);

-- Dedupe by user (keep latest row) in users.
with ranked as (
  select ctid,
         row_number() over (partition by id order by last_active desc nulls last, joined_at desc nulls last, ctid desc) as rn
  from public.users
)
delete from public.users u
using ranked r
where u.ctid = r.ctid
  and r.rn > 1;

-- Dedupe payments by provider_txn_id when available (keep latest).
with ranked as (
  select ctid,
         row_number() over (partition by provider_txn_id order by created_at desc nulls last, ctid desc) as rn
  from public.payments
  where provider_txn_id is not null
)
delete from public.payments p
using ranked r
where p.ctid = r.ctid
  and r.rn > 1;

-- Trim heavy logs (keep recent 90 days).
delete from public.action_logs
where created_at < now() - interval '90 days';

delete from public.system_logs
where created_at < now() - interval '90 days';

-- NOTE: Direct DELETE on storage.objects is blocked in Supabase SQL editor.
-- Orphan object cleanup must be done via Storage API/CLI with service-role credentials.

-- ============================================================================
-- 8) PERFORMANCE OPTIMIZATION
-- ============================================================================

-- Tighten datatypes/defaults and check constraints.
alter table if exists public.users
  alter column files_processed set default 0,
  alter column sessions set default 0;

alter table if exists public.users
  add constraint users_files_processed_nonneg check (files_processed >= 0) not valid,
  add constraint users_sessions_nonneg check (sessions >= 0) not valid;

alter table if exists public.payments
  add constraint payments_amount_nonneg check (amount_uzs is null or amount_uzs >= 0) not valid,
  add constraint payments_plan_type_check check (lower(plan_type::text) in ('cv','objective','obyektivka')) not valid,
  add constraint payments_status_check check (status::text in ('pending','approved','rejected','paid','failed','cancelled')) not valid;

alter table if exists public.paid_doc_requests
  add constraint paid_doc_requests_kind_check check (lower(kind::text) in ('cv','objective','obyektivka')) not valid,
  add constraint paid_doc_requests_status_check check (status::text in ('pending','approved','rejected','completed','cancelled')) not valid;

alter table if exists public.support_requests
  add constraint support_requests_status_check check (status::text in ('open','resolved','closed')) not valid;

-- Validate constraints after cleanup.
alter table if exists public.users validate constraint users_files_processed_nonneg;
alter table if exists public.users validate constraint users_sessions_nonneg;
alter table if exists public.payments validate constraint payments_amount_nonneg;
alter table if exists public.payments validate constraint payments_plan_type_check;
alter table if exists public.payments validate constraint payments_status_check;
alter table if exists public.paid_doc_requests validate constraint paid_doc_requests_kind_check;
alter table if exists public.paid_doc_requests validate constraint paid_doc_requests_status_check;
alter table if exists public.support_requests validate constraint support_requests_status_check;

-- Update planner stats.
analyze public.users;
analyze public.payments;
analyze public.paid_doc_requests;
analyze public.support_requests;
analyze public.action_logs;
analyze public.system_logs;

-- ============================================================================
-- 9) SECURITY OPTIMIZATION
-- ============================================================================

-- Ensure tables are not accidentally exposed via broad grants.
revoke all on table public.users from anon, authenticated;
revoke all on table public.payments from anon, authenticated;
revoke all on table public.paid_doc_requests from anon, authenticated;
revoke all on table public.support_requests from anon, authenticated;
revoke all on table public.action_logs from anon, authenticated;
revoke all on table public.system_logs from anon, authenticated;

-- Grant only required read/write paths (RLS still applies).
grant select, update on public.users to authenticated;
grant select on public.payments to authenticated;
grant select on public.paid_doc_requests to authenticated;
grant select, insert on public.support_requests to authenticated;

-- Lock down legacy trigger cleanup: remove suspicious old triggers in public.
do $$
declare
  r record;
begin
  for r in
    select event_object_table as table_name, trigger_name
    from information_schema.triggers
    where trigger_schema = 'public'
      and (
        trigger_name ilike '%premium%'
        or trigger_name ilike '%referral%'
        or trigger_name ilike '%ocr%'
        or trigger_name ilike '%translate%'
        or trigger_name ilike '%translit%'
        or trigger_name ilike '%spell%'
        or trigger_name ilike '%bucket%'
        or trigger_name ilike '%subscription%'
        or trigger_name ilike '%experiment%'
      )
  loop
    execute format('drop trigger if exists %I on public.%I', r.trigger_name, r.table_name);
    raise notice 'Dropped legacy trigger: public.%.%', r.table_name, r.trigger_name;
  end loop;
end$$;

-- ============================================================================
-- 10) FINAL CLEAN STRUCTURE
-- ============================================================================

-- Primary keys and FKs (add only if absent).
do $$
begin
  if exists (select 1 from information_schema.tables where table_schema='public' and table_name='users')
     and not exists (
       select 1
       from pg_constraint con
       join pg_class cls on cls.oid = con.conrelid
       join pg_namespace nsp on nsp.oid = cls.relnamespace
       where nsp.nspname = 'public'
         and cls.relname = 'users'
         and con.contype = 'p'
     ) then
    alter table public.users
      add constraint users_pkey primary key (id);
  end if;
exception when duplicate_table or duplicate_object or invalid_table_definition then
  null;
end$$;

do $$
begin
  if exists (select 1 from information_schema.tables where table_schema='public' and table_name='payments')
     and not exists (
       select 1
       from pg_constraint con
       join pg_class cls on cls.oid = con.conrelid
       join pg_namespace nsp on nsp.oid = cls.relnamespace
       where nsp.nspname = 'public'
         and cls.relname = 'payments'
         and con.contype = 'p'
     ) then
    alter table public.payments
      add constraint payments_pkey primary key (id);
  end if;
exception when duplicate_table or duplicate_object or invalid_table_definition then
  null;
end$$;

do $$
begin
  if exists (select 1 from information_schema.tables where table_schema='public' and table_name='paid_doc_requests')
     and not exists (
       select 1
       from pg_constraint con
       join pg_class cls on cls.oid = con.conrelid
       join pg_namespace nsp on nsp.oid = cls.relnamespace
       where nsp.nspname = 'public'
         and cls.relname = 'paid_doc_requests'
         and con.contype = 'p'
     ) then
    alter table public.paid_doc_requests
      add constraint paid_doc_requests_pkey primary key (id);
  end if;
exception when duplicate_table or duplicate_object or invalid_table_definition then
  null;
end$$;

alter table if exists public.payments
  drop constraint if exists payments_user_id_fkey,
  add constraint payments_user_id_fkey
    foreign key (user_id) references public.users(id) on delete cascade;

alter table if exists public.paid_doc_requests
  drop constraint if exists paid_doc_requests_user_id_fkey,
  add constraint paid_doc_requests_user_id_fkey
    foreign key (user_id) references public.users(id) on delete cascade;

alter table if exists public.paid_doc_requests
  drop constraint if exists paid_doc_requests_payment_id_fkey,
  add constraint paid_doc_requests_payment_id_fkey
    foreign key (payment_id) references public.payments(id) on delete set null;

alter table if exists public.support_requests
  drop constraint if exists support_requests_user_id_fkey,
  add constraint support_requests_user_id_fkey
    foreign key (user_id) references public.users(id) on delete cascade;

-- Helpful final visibility report.
do $$
declare r record;
begin
  raise notice '=== FINAL PUBLIC TABLES ===';
  for r in
    select table_name
    from information_schema.tables
    where table_schema='public' and table_type='BASE TABLE'
    order by table_name
  loop
    raise notice 'public.%', r.table_name;
  end loop;
end$$;

commit;
