-- Paid single-document requests (CV / Obyektivka)
-- Run in Supabase SQL editor once.

create table if not exists public.paid_doc_requests (
  id bigserial primary key,
  user_id bigint not null references public.users(id) on delete cascade,
  kind text not null check (kind in ('cv','obyektivka')),
  payload jsonb not null,
  status text not null default 'pending',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists paid_doc_requests_user_id_idx on public.paid_doc_requests(user_id);
create index if not exists paid_doc_requests_status_idx on public.paid_doc_requests(status);

-- Keep updated_at fresh
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_paid_doc_requests_updated_at on public.paid_doc_requests;
create trigger trg_paid_doc_requests_updated_at
before update on public.paid_doc_requests
for each row execute function public.set_updated_at();

