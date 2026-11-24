-- Smart PDF Compressor: one UTR = one payment. Run once in Supabase -> SQL Editor -> New query -> Run
-- Rejected orders are ignored, so the real payer can still submit a UTR that was rejected for someone else.

-- If the last command fails, duplicates already exist. See them with:
--   select utr, count(*) from public.upgrade_requests
--   where utr <> '' and status in ('submitted', 'paid', 'approved') group by utr having count(*) > 1;

create unique index if not exists upgrade_requests_utr_unique on public.upgrade_requests (utr)
    where utr <> '' and status in ('submitted', 'paid', 'approved');
