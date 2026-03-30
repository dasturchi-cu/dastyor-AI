-- Referral + discount schema (SQL Editor'da run qiling)
-- Maqsad:
-- 1) /start ref_<id> orqali kelgan yangi user invitee bo'ladi
-- 2) inviter_id uchun referrals_count oshadi
-- 3) 5 ta referral bo'lsa: Standard/Premium uchun 30% discount flag yoqiladi

alter table public.users add column if not exists referred_by bigint;
alter table public.users add column if not exists referrals_count integer not null default 0;
alter table public.users add column if not exists referral_discount_percent integer not null default 0;
alter table public.users add column if not exists referral_discount_active boolean not null default false;
alter table public.users add column if not exists referral_discount_expires_at timestamptz;

-- Per-plan 1-time discount flags (Standard and Premium separately)
alter table public.users add column if not exists referral_discount_standard_active boolean not null default false;
alter table public.users add column if not exists referral_discount_premium_active boolean not null default false;
alter table public.users add column if not exists referral_discount_standard_consumed_at timestamptz;
alter table public.users add column if not exists referral_discount_premium_consumed_at timestamptz;

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

  -- 5 ta bo'lsa: discount yoqiladi (30%) — har plan uchun ALohida 1 martadan.
  -- Standard va Premium: consumed_at bo'lsa qayta yoqilmaydi.
  if cnt >= 5 then
    update public.users
      set referral_discount_percent = 30,
          referral_discount_standard_active = case
            when referral_discount_standard_consumed_at is null then true
            else referral_discount_standard_active
          end,
          referral_discount_premium_active = case
            when referral_discount_premium_consumed_at is null then true
            else referral_discount_premium_active
          end,
          referral_discount_active = (
            (case when referral_discount_standard_consumed_at is null then true else referral_discount_standard_active end)
            or
            (case when referral_discount_premium_consumed_at is null then true else referral_discount_premium_active end)
          )
      where id = inviter;
  end if;

  return json_build_object('ok', true, 'inserted', inserted, 'referrals_count', cnt);
end;
$$;

-- Discountni ishlatgandan keyin o'chirish (har plan uchun 1 martadan)
create or replace function public.consume_referral_discount(uid bigint, plan text)
returns json
language plpgsql
security definer
as $$
declare
  pct integer := 0;
  p text := '';
  std_active boolean := false;
  prem_active boolean := false;
begin
  if uid is null then
    return json_build_object('ok', false, 'reason', 'missing');
  end if;
  p := lower(coalesce(plan, ''));
  if p not in ('standard','premium') then
    return json_build_object('ok', false, 'reason', 'bad_plan');
  end if;

  select coalesce(referral_discount_percent, 0),
         coalesce(referral_discount_standard_active, false),
         coalesce(referral_discount_premium_active, false)
    into pct, std_active, prem_active
    from public.users where id = uid;

  if coalesce(pct, 0) <= 0 then
    return json_build_object('ok', true, 'consumed', false, 'percent', 0);
  end if;

  if p = 'standard' then
    if not std_active then
      return json_build_object('ok', true, 'consumed', false, 'percent', pct);
    end if;
    update public.users
      set referral_discount_standard_active = false,
          referral_discount_standard_consumed_at = now()
      where id = uid;
  else
    if not prem_active then
      return json_build_object('ok', true, 'consumed', false, 'percent', pct);
    end if;
    update public.users
      set referral_discount_premium_active = false,
          referral_discount_premium_consumed_at = now()
      where id = uid;
  end if;

  -- keep legacy aggregated fields in sync (for older clients)
  update public.users
    set referral_discount_active = (coalesce(referral_discount_standard_active, false) or coalesce(referral_discount_premium_active, false)),
        referral_discount_expires_at = case
          when (coalesce(referral_discount_standard_active, false) or coalesce(referral_discount_premium_active, false)) then referral_discount_expires_at
          else now()
        end
    where id = uid;

  return json_build_object('ok', true, 'consumed', true, 'percent', pct, 'plan', p);
end;
$$;

grant execute on function public.consume_referral_discount(bigint, text) to anon, authenticated;

-- RLS bo'lsa: backend anon key bilan ishlashi uchun RPCga ruxsat bering.
-- (Siz service_role ishlatsangiz ham bo'ladi.)
grant execute on function public.register_referral(bigint, bigint) to anon, authenticated;

