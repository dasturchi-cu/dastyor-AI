-- Bir martalik to'lov: status qiymatlari (agar cleanup_minimal_platform.sql ishlatilgan bo'lsa).
-- SQL Editor da bir marta ishga tushiring.

alter table if exists public.paid_doc_requests
  drop constraint if exists paid_doc_requests_status_check;

alter table if exists public.paid_doc_requests
  add constraint paid_doc_requests_status_check
  check (
    status::text in (
      'pending',
      'pending_payment',
      'payment_submitted',
      'approved',
      'rejected',
      'completed',
      'cancelled',
      'delivered'
    )
  );

update public.paid_doc_requests
set status = 'pending'
where status in ('pending_payment', 'payment_submitted');

update public.paid_doc_requests
set status = 'completed'
where status = 'delivered';
