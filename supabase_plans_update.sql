-- Smart PDF Compressor: admin-editable plans. Run once in Supabase -> SQL Editor -> New query -> Run
create table if not exists public.app_settings (
    key        text primary key,
    value      jsonb,
    updated_at timestamptz default now()
);
alter table public.app_settings enable row level security;
grant select, insert, update, delete on public.app_settings to service_role;
