-- Referral + discount schema (SQL Editor'da run qiling)
-- Maqsad:
-- 1) /start ref_<id> orqali kelgan yangi user invitee bo'ladi
-- 2) inviter_id uchun referrals_count oshadi
-- 3) 5 ta referral bo'lsa: premium uchun 30% discount flag yoqiladi

alter table public.users add column if not exists referred_by bigint;
alter table public.users add column if not exists referrals_count integer not null default 0;
alter table public.users add column if not exists referral_discount_percent integer not null default 0;
alter table public.users add column if not exists referral_discount_active boolean not null default false;
alter table public.users add column if not exists referral_discount_expires_at timestamptz;

create table if not exists public.referrals (
  id bigserial primary key,
  inviter_id bigint not null,
  invitee_id bigint not null unique,
  created_at timestamptz not null default now()
);

create index if not exists idx_referrals_inviter on public.referrals(inviter_id);

-- Atomik referral register: invitee bir marta
create or replace function public.register_referral(inviter bigint, invitee bigint)
returns json
language plpgsql
security definer
as $$
declare
  inserted boolean := false;
  cnt integer := 0;
begin
  if inviter is null or invitee is null then
    return json_build_object('ok', false, 'reason', 'missing');
  end if;
  if inviter = invitee then
    return json_build_object('ok', false, 'reason', 'self');
  end if;

  begin
    insert into public.referrals(inviter_id, invitee_id) values(inviter, invitee);
    inserted := true;
  exception when unique_violation then
    inserted := false;
  end;

  -- ensure invitee has referred_by set (best effort)
  update public.users set referred_by = inviter
    where id = invitee and (referred_by is null);

  if inserted then
    update public.users
      set referrals_count = coalesce(referrals_count, 0) + 1
      where id = inviter;
  end if;

  select coalesce(referrals_count, 0) into cnt from public.users where id = inviter;

  -- 5 ta bo'lsa: discount yoqiladi (30%)
  if cnt >= 5 then
    update public.users
      set referral_discount_percent = 30,
          referral_discount_active = true
      where id = inviter;
  end if;

  return json_build_object('ok', true, 'inserted', inserted, 'referrals_count', cnt);
end;
$$;

-- RLS bo'lsa: backend anon key bilan ishlashi uchun RPCga ruxsat bering.
-- (Siz service_role ishlatsangiz ham bo'ladi.)
grant execute on function public.register_referral(bigint, bigint) to anon, authenticated;

