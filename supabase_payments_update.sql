-- Smart PDF Compressor: payments update. Run once in Supabase -> SQL Editor -> New query -> Run
-- Adds payment fields to the upgrade_requests table (safe to run more than once).

alter table public.upgrade_requests add column if not exists amount_inr  integer default 0;
alter table public.upgrade_requests add column if not exists method      text    default 'manual';  -- upi
alter table public.upgrade_requests add column if not exists order_ref   text    default '';
alter table public.upgrade_requests add column if not exists utr         text    default '';        -- UPI transaction id
alter table public.upgrade_requests add column if not exists gateway_ref text    default '';        -- reserved
alter table public.upgrade_requests add column if not exists qr_url      text    default '';
alter table public.upgrade_requests add column if not exists paid_at     timestamptz;

create index if not exists upgrade_requests_email_status on public.upgrade_requests (email, status);

-- the server key needs access (same as before)
grant select, insert, update, delete on all tables in schema public to service_role;
grant usage, select on all sequences in schema public to service_role;
